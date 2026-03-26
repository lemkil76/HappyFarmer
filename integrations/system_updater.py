"""
HappyFarmer – Systemuppdaterare
integrations/system_updater.py
Revised by Claude - 2026-03-26

Kör apt-uppdateringar på Pi:n och loggar resultatet till MariaDB.
Kan anropas manuellt, via admin-API:t eller som ett cron-jobb.

Körs direkt:
    python3 -m integrations.system_updater

Via cron (varannan vecka, söndag kl 03:00):
    0 3 */14 * 0 cd /home/pi/happyfarmer && python3 -m integrations.system_updater
"""

import subprocess
import time
import sys
import platform
import logging

from integrations import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("happyfarmer.updater")


def get_system_info() -> dict:
    """Hämtar OS-, kernel- och Python-version."""
    try:
        os_ver = subprocess.check_output(
            ["lsb_release", "-ds"], stderr=subprocess.DEVNULL, text=True
        ).strip()
    except Exception:
        os_ver = platform.platform()

    return {
        "os_version":     os_ver,
        "kernel_version": platform.release(),
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    }


def check_available_updates() -> list[str]:
    """
    Returnerar lista med paket som kan uppdateras.
    Kör 'apt update' tyst och listar sedan tillgängliga uppgraderingar.
    """
    log.info("Kontrollerar tillgängliga uppdateringar…")
    try:
        subprocess.run(
            ["sudo", "apt-get", "update", "-qq"],
            check=True, capture_output=True, timeout=120,
        )
        result = subprocess.run(
            ["apt-get", "--simulate", "upgrade"],
            capture_output=True, text=True, timeout=60,
        )
        packages = []
        for line in result.stdout.splitlines():
            if line.startswith("Inst "):
                parts = line.split()
                if len(parts) >= 2:
                    packages.append(parts[1])
        log.info(f"{len(packages)} paket tillgängliga: {', '.join(packages) or 'inga'}")
        return packages
    except subprocess.TimeoutExpired:
        log.error("apt update tog för lång tid – avbröt")
        return []
    except Exception as e:
        log.error(f"check_available_updates fel: {e}")
        return []


def run_updates(dry_run: bool = False) -> dict:
    """
    Kör apt-get upgrade och loggar resultatet till MariaDB.

    Args:
        dry_run: Om True körs bara kontroll, inga ändringar görs.

    Returnerar dict med status, packages_updated, packages_list, duration_sec.
    """
    sysinfo    = get_system_info()
    start_time = time.time()

    log.info(f"System: {sysinfo['os_version']} | Kernel: {sysinfo['kernel_version']}")

    available = check_available_updates()

    if not available:
        log.info("Inga uppdateringar tillgängliga.")
        db.log_system_update(
            status           = "no_updates",
            packages_updated = 0,
            packages_list    = None,
            duration_sec     = int(time.time() - start_time),
            notes            = "Inga uppdateringar tillgängliga",
            **sysinfo,
        )
        return {
            "status":           "no_updates",
            "packages_updated": 0,
            "packages_list":    [],
            "duration_sec":     int(time.time() - start_time),
        }

    if dry_run:
        log.info(f"[DRY RUN] Skulle uppdatera {len(available)} paket: {', '.join(available)}")
        return {
            "status":           "dry_run",
            "packages_updated": len(available),
            "packages_list":    available,
            "duration_sec":     int(time.time() - start_time),
        }

    log.info(f"Uppgraderar {len(available)} paket…")
    try:
        result = subprocess.run(
            ["sudo", "apt-get", "upgrade", "-y",
             "-o", "Dpkg::Options::=--force-confold"],
            capture_output=True, text=True, timeout=600,
        )
        duration = int(time.time() - start_time)

        if result.returncode == 0:
            status = "success"
            log.info(f"Uppdatering klar på {duration}s – {len(available)} paket")
        else:
            status = "failed"
            log.error(f"apt-get upgrade misslyckades:\n{result.stderr[:500]}")

        db.log_system_update(
            status           = status,
            packages_updated = len(available) if status == "success" else 0,
            packages_list    = ", ".join(available),
            duration_sec     = duration,
            notes            = result.stderr[:500] if status == "failed" else None,
            **sysinfo,
        )
        return {
            "status":           status,
            "packages_updated": len(available) if status == "success" else 0,
            "packages_list":    available,
            "duration_sec":     duration,
        }

    except subprocess.TimeoutExpired:
        duration = int(time.time() - start_time)
        log.error("apt-get upgrade: timeout efter 10 min")
        db.log_system_update(
            status="failed", packages_updated=0,
            notes="Timeout efter 600s", duration_sec=duration, **sysinfo,
        )
        return {"status": "failed", "packages_updated": 0,
                "packages_list": available, "duration_sec": duration}

    except Exception as e:
        duration = int(time.time() - start_time)
        log.error(f"Oväntat fel vid uppdatering: {e}")
        db.log_system_update(
            status="failed", packages_updated=0,
            notes=str(e), duration_sec=duration, **sysinfo,
        )
        return {"status": "failed", "packages_updated": 0,
                "packages_list": [], "duration_sec": duration}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="HappyFarmer systemuppdaterare")
    parser.add_argument("--dry-run", action="store_true",
                        help="Kontrollera utan att installera")
    parser.add_argument("--check",   action="store_true",
                        help="Visa bara tillgängliga uppdateringar")
    args = parser.parse_args()

    if args.check:
        pkgs = check_available_updates()
        if pkgs:
            print(f"\n{len(pkgs)} uppdatering(ar) tillgänglig(a):")
            for p in pkgs:
                print(f"  • {p}")
        else:
            print("Systemet är uppdaterat.")
    else:
        result = run_updates(dry_run=args.dry_run)
        print(f"\nResultat: {result['status']} | "
              f"Paket: {result['packages_updated']} | "
              f"Tid: {result['duration_sec']}s")

        last = db.get_last_system_update()
        if last:
            print(f"Loggat i DB: {last['updated_at']} – {last['status']}")
