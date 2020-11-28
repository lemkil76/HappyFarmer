import twitter

# ******************  OBS Production Code *****************
api = twitter.Api(consumer_key='your key',
                      consumer_secret='your secret',
                      access_token_key='your token key',
                      access_token_secret='your token secret')

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






