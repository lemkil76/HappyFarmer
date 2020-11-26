# HappyFarmer
Fully automated grow tower system for modern happy farmers.

Vertical farming is an exiting field and the goal is to have a system in every house that basically takes care of itself. The growing is done in vertical tubes with slots for the plants and water is sprayed inside the main tube. There is no soil in the grow tower instead we use water and air. The water pump cycles between on and off to let the roots get airrated but not dry or too wet.

The system is based on a Raspberry Pi platform and runs Apache and Python. The main code is monitoring the system and runs a normal operation cycle. The cycle drives relays that turns on/off, water heater, water pump, grow lights and a heater/fan.

System has 4 sensors.
Water temperature
Air temperature
Humidity
Foto resistor
