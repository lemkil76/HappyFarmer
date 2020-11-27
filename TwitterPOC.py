import twitter

# ******************  OBS Production Code *****************
api = twitter.Api(consumer_key='mjXEXaJQTJzKqtQ1O7nYYcmvw',
                      consumer_secret='cI20chhiyRSrqNDUsmIsqcEpjImRBh8Wpx9FgJMRP8mG6Fj8g1',
                      access_token_key='523052157-Wkvget4SfO7hIVcQ5YT2ODLG7at6ckeofXyEICum',
                      access_token_secret='kujSji5QFKTgHGWZe0vgp4BUTSKLroTCwqH5M2COq9TpX')

#api.PostUpdate("Hello World! from python and twitter API")

# *********************************************************



#me = api.VerifyCredentials()

import os

print()


stream_url = api.stream_url
#print(stream_url)

users = api.GetFriends()
print([u.name for u in users])



comment_lib = ['Glad bonde önskar dig en härlig dag!',
               'Här kan du följa progressen på bygget',
               'Glad bonde använder python och Raspberry pi',
               'Sensorer som finns: Temperatursensor luft och vatten, luftfuktighet, fotoresistor'] 

#print(comment_lib[3])






