import re
import datetime
from nltk.tokenize import TreebankWordTokenizer
from pickle import load
from nltk.stem import *
from nltk.stem.porter import *


#eventadd
def initialise():
  with open('./data/data.pickle', 'rb') as handle:
    data = load(handle)

  emojis = data["emojis"]
  months = data["months"]
  timewords_day = data["timewords_day"]
  commands = data["commands"]

  return emojis, months, timewords_day, commands


def processing_eventadd(message):
  emojis, months, timewords_day, commands = initialise()
  with open('./data/1.pkl', 'rb') as f:
    tagger = load(f)

  #Load stemmer
  stemmer = PorterStemmer()
  tokenizer = TreebankWordTokenizer()

  text = message.lower()
  list = tokenizer.tokenize(text)[1:]
  stemmed = [stemmer.stem(i) for i in list]

  #Check if there is text following /eventadd
  if len(list) < 4:
    return [
      "Usage: $eventadd text \nText following command should preferably include event name, date, location, time"
    ]

  tagged = tagger.tag(list)
  tags = [i for (__, i) in tagged]
  date = ""
  places = []
  firstnouns = []
  nouns = []
  timeword = 0
  time = ""
  h = 0
  m = 0

  #Taking first consecutive noun group
  try:
    i = tags.index("NN")
    while tags[i] == "NN":
      if tagged[i][0] in timewords_day or re.fullmatch(
          "^[0-9]{1,2}((.|:)[0-9]{2}){0,1}[a,p]m$",
          tagged[i][0]) is not None or re.fullmatch(
            "^[0-9]{1,2}:[0-9]{2}[h]{0,1}$", tagged[i][0]) is not None:
        break
      firstnouns.append(tagged[i][0])
      i += 1

  #Returns error if there was no nouns in text
  except (IndexError, ValueError):
    return [
      "There was no nouns in the text\n\nUsage: $eventadd text \nText following command should preferably include event name, date, location, time"
    ]

  #Timeword
  for i in timewords_day.keys():
    if i in text:
      timeword = timewords_day[i]

  for i in range(len(tagged)):
    #Retriving date from message

    #Check for time
    #12h 1 number time
    if re.fullmatch("^[0-9]{1,2}[a,p]m$", tagged[i][0]):
      time = tagged[i][0]
      a = time.find("a")
      p = time.find("p")
      b = a if p == -1 else p
      h = int(time[:b]) % 12 if p == -1 else (int(time[:b]) + 12) % 24

    #12h
    elif re.fullmatch("^[0-9]{1,2}((.|:)[0-9]{2}){0,1}[a,p]m$", tagged[i][0]):
      time = tagged[i][0]
      a = time.find("a")
      p = time.find("p")
      c = time.find(".") if time.find(":") == -1 else time.find(":")
      b = a if p == -1 else p
      h = int(time[:c]) % 12 if p == -1 else (int(time[:c]) + 12) % 24
      m = int(time[c + 1:b])

    #24h
    elif re.fullmatch("^[0-9]{1,2}:[0-9]{2}[h]{0,1}$", tagged[i][0]):
      time = tagged[i][0]
      c = time.find(":")
      b = time.find("h")
      h = int(time[:c]) % 24
      m = int(time[c + 1:]) if b == -1 else int(time[c + 1:b])

    #Check for XX month structure
    current_year = datetime.date.today().year
    if tagged[i][1] == "CD" and int(tagged[i][0]) < 32:
      try:
        if tagged[i + 1][0] in months:
          month = months[tagged[i + 1][0]]
          day = int(tagged[i][0])
          date = datetime.datetime(current_year, month, day)

          # Add a year if already past
          if date < datetime.datetime.now():
            date = datetime.datetime(current_year + 1, month, day)
      except IndexError:
        continue

    #Check for month XX structure
    elif tagged[i][0] in months:
      try:
        if tagged[i + 1][1] == "CD" and int(tagged[i + 1][0]) < 32:
          month = months[tagged[i][0]]
          day = int(tagged[i + 1][0])
          date = datetime.datetime(current_year, month, day)

          # Add a year if already past
          if date < datetime.datetime.now():
            date = datetime.datetime(current_year + 1, month, day)
      except IndexError:
        continue

  #Add to nouns
    if re.fullmatch("NN[A-Z]{0,1}", tagged[i][1]):
      nouns.append(tagged[i][0])

  #Check for places
    if tagged[i][0] == "at":
      j = i + 1
      if j < len(tagged):
        while re.fullmatch("(NN[A-Z]{0,1}|CC|DT)", tagged[j][1]) != None:
          if re.fullmatch(
              "^[0-9]{1,2}((.|:)[0-9]{2}){0,1}[a,p]m$",
              tagged[j][0]) is not None or re.fullmatch(
                "^[0-9]{1,2}:[0-9]{2}[h]{0,1}$",
                tagged[j][0]) is not None or tagged[j][0] in timewords_day:
            break
          places.append(tagged[j][0])
          if j == len(tagged) - 1:
            break
          j += 1

  if len(places) == 0:
    for i in range(len(tagged)):
      if stemmed[i] in ["walk", "go", "drive", "take"]:
        while i < len(tagged):
          if tagged[i][0] in ["to", "back"] and re.fullmatch(
              "NN[A-Z]{0,1}", tagged[i + 1][1]):
            for j in range(i + 1, len(tagged)):
              if re.fullmatch(
                  "NN[A-Z]{0,1}", tagged[j][1]) == None or re.fullmatch(
                    "^[0-9]{1,2}((.|:)[0-9]{2}){0,1}[a,p]m$",
                    tagged[j][0]) is not None or re.fullmatch(
                      "^[0-9]{1,2}:[0-9]{2}[h]{0,1}$", tagged[j]
                      [0]) is not None or tagged[j][0] in timewords_day:
                break
              places.append(tagged[j][0])
            break
          elif i == len(tagged) - 1:
            break
          i += 1

  date = (datetime.datetime.combine(datetime.date.today(), datetime.time.min) +
          datetime.timedelta(days=timeword, hours=h, minutes=m)
          ) if date == "" else datetime.datetime.combine(
            date, datetime.time.min) + datetime.timedelta(hours=h, minutes=m)

  return [firstnouns, places, date]


#eventremove

#eventshow
