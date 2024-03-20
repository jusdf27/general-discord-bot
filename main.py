import discord
import os
import random
import re
import datetime
import sqlite3
import logging

from pickle import load
from nltk.stem import *
from nltk.stem.porter import *
from discord.ext import commands
from helper import processing_eventadd, initialise

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="$", intents=intents)


@bot.event
async def on_ready():
  print(f'We have logged in as {bot.user}')


#Loading list and dict
with open('./data/data.pickle', 'rb') as handle:
  data = load(handle)

emojis = data["emojis"]
months = data["months"]
timewords_day = data["timewords_day"]
commands = data["commands"]

# Stores 
eventaddauthors = {}


"""
BOT COMMANDS BOT COMMANDS BOT COMMANDS BOT COMMANDS BOT COMMANDS BOT COMMANDS BOT COMMANDS 
"""
@bot.command("poll")
async def poll(ctx, *args):

  logging.info("poll command detected")
  poll_options = list(args)
  l = len(poll_options)

  #Error handling
  if l == 0:
    await ctx.reply(
      "Usage: $poll choice1 choice2 choice3...\nSupports up to 9 choices")
    return

  m = max([len(i) for i in poll_options])

  if l > 9:
    await ctx.reply("Poll function only supports up to 9 choices")
    return

  #Concatenating poll content
  emoji = []
  reply = "```\nPOLL\n"
  for i in range(l):
    optionheader = emojis[i] + ": " + poll_options[i]
    replybuffer = optionheader + (" " *
                                  (10 + m - len(optionheader))) + "Vote: 0  \n"
    emoji.append(i)
    reply += replybuffer
  reply += "```"
  output = await ctx.send(reply)
  logging.info("poll message outputed")

  #Adding reactions for poll input
  logging.info("Adding initial reactions to Poll message")
  for i in emoji:
    await output.add_reaction(emojis[i])
  return


@bot.command("rng")
async def rng(ctx, *args):
  logging.info("rng command detected")
  args = list(args)

  #Ensure 1st arg is number
  try:
    num = int(args[0])
  except (ValueError, IndexError):
    await ctx.reply("Usage: $rng number option1 option2 option3 ...")
    logging.warning("Rejecting rng command due to invalid usage")
    return

  #Ensure at least 2 args
  if len(args) <= 1:
    await ctx.reply("Usage: $rng number option1 option2 option3 ...")
    logging.warning("Rejecting rng command due to invalid usage")
    return

  #Check that number specified is more than number of options given
  if num > len(args) - 1:
    await ctx.reply(
      "Number to be randomised is more than number of options given")
    logging.warning("Rejecting rng command due to invalid usage")
    return

  options = [args[i] for i in range(1, len(args))]
  chosen = random.sample(options, k=num)
  output = ""
  for i in chosen:
    output += i + " "
  output = output.strip()
  await ctx.send(output)
  logging.info("rng message outputed")
  return


@bot.command("eventadd")
async def eventadd(ctx, *args):

  logging.info("eventadd command detected")
  message = " ".join(list(args))
  process_output = processing_eventadd(message)
  print(process_output)
  if len(process_output) == 1:
    await ctx.reply(process_output[0])
    return

  firstnouns, places, date = process_output[0], process_output[
    1], process_output[2]

  output = await ctx.send(
    "```\nADDING EVENT\nEvent: " + ' '.join(firstnouns).title() +
    "\nLocation: " + ' '.join(places).title() + "\nDate: " +
    str(datetime.datetime.strptime(str(date), '%Y-%m-%d %H:%M:%S')) + " ```")
  firstnouns = " ".join(firstnouns).strip()
  places = " ".join(places).strip()
  eventaddauthors[output.id] = (ctx.author.id, date, firstnouns, places)
  logging.info("eventadd message outputed")

  #Adding reactions for poll input
  logging.info("Adding initial reactions to eventadd message")
  await output.add_reaction("✅")
  await output.add_reaction("❎")
  return


@bot.command("eventremove")
async def eventremove(ctx, *id):
  logging.info("eventremove command detected")
  id = list(id)
  if len(id) != 1:
    await ctx.send("Usage: $eventremove ID")
    logging.warning("Rejecting $eventremove command due to invalid usage")
    return

  try:
    eventid = int(id[0])
  except TypeError:
    await ctx.send("Usage: $eventremove ID \nID is an integer.")
    logging.warning("Rejecting $eventremove command due to invalid usage")
    return

  con = sqlite3.connect("discordbotevent.db")
  cur = con.cursor()
  eventdata = cur.execute("SELECT * FROM events WHERE id = ?",
                          (eventid, )).fetchall()
  if len(eventdata) < 1:
    await ctx.send("Invalid ID. Use $eventshow to check for recorded events.")
    logging.warning("Rejecting $eventremove command due to invalid usage")
    return

  reply = "```Confirm to remove the following event? \n\n"

  for row in eventdata:
    reply += "Id: " + str(row[0]) + "\n"
    reply += "Event: " + row[1].title() + "\n"
    reply += "Location: " + row[2].title() + "\n"
    reply += "Date: " + str(datetime.datetime.fromtimestamp(
      row[3] / 1000.0)) + "\n"
    reply += "\n"
  reply += "```"
  output = await ctx.send(reply)
  logging.info("eventremove message outputed")
  con.close()

  eventaddauthors[output.id] = (ctx.author.id, row[0])

  #Adding reactions for confirmation input
  print(
    str(datetime.datetime.now()) +
    " Adding initial Reactions to EventRemove message")
  await output.add_reaction("✅")
  await output.add_reaction("❎")
  return


@bot.command("eventshow")
async def eventshow(ctx):
  logging.info("eventshow command detected")

  with sqlite3.connect("discordbotevent.db") as con:
    cur = con.cursor()
    eventdata = cur.execute("SELECT * FROM events").fetchall()
    reply = "```Current Events:\n\n"
    for row in eventdata:
      reply += "Id: " + str(row[0]) + "\n"
      reply += "Event: " + row[1].title() + "\n"
      reply += "Location: " + row[2].title() + "\n"
      reply += "Date: " + str(datetime.datetime.fromtimestamp(
        row[3] / 1000.0)) + "\n"
      reply += "\n"
    reply += "```"
  await ctx.send(reply)
  logging.info("eventShow command outputed")
  return


#HELP COMMAND
@bot.command("help$")
async def help(ctx, *args):
  args = list(args)

  #Help to see avaliable commands
  if len(args) == 0:
    reply = "Avaliable commands are: "
    for i in commands.keys():
      reply += " **" + i + "** "
    await ctx.reply(reply)
    logging.info("help message outputed")
    return

  #Help for individual commands (Using commands dict above)
  if len(args) >= 1:
    if args[1] not in commands.keys():
      await ctx.reply("No corresponding commands")
      logging.warning("Rejecting $help$ command due to invalid usage")
      return
    else:
      for i, c in enumerate(args):
        reply = "**" + c + "**\n" + commands[c]
        await ctx.reply(reply)
      return
  else:
    await ctx.reply("Usage: $help$ command_name")
    logging.warning("Rejecting $help$ command due to invalid usage")
    return

#MANAGING REACTION ADD
@bot.event
async def on_raw_reaction_add(payload):
  counts = []
  channel = bot.get_channel(payload.channel_id)
  message = await channel.fetch_message(payload.message_id)
  user = await bot.fetch_user(payload.user_id)

  #Ensure only on bot's message
  if message.author != bot.user:
    return

  #POLL REACTIONS
  if message.content.startswith("```\nPOLL"):
    logging.info("Reaction added to Poll message")
    numoptions = len(
      [m.span()[1] for m in re.finditer("Vote: ", message.content)])
    checkemoji = [emojis[i] for i in range(numoptions)]

    #Checking existing emojis are legal
    for r in message.reactions:
      if str(r) not in checkemoji:
        logging.info("Removing illegal reactions from Poll message")
        await message.remove_reaction(r, user)

    #Counting number of votes using reactions
    for r in message.reactions:
      counts.append(r.count - 1)

    #Updating message with votes
    text = message.content
    voteref = [m.span()[1] for m in re.finditer("Vote: ", text)]
    for i in reversed(range(len(voteref))):
      text = text[:voteref[i]] + str(counts[i]) + text[voteref[i] + 1:]
    await message.edit(content=text)

  #EVENTREMOVE REACTIONS
  if message.content.startswith(
      "```Confirm to remove the following event? \n"):
    logging.info("Reaction added to EventRemove message")
    checkemoji = [emojis[i] for i in range(9, 11)]

    #Checking existing emojis are legal
    for r in message.reactions:
      if str(r) not in checkemoji:
        logging.info("Removing illegal reactions from Poll message")
        await message.remove_reaction(r, user)

    #Checking for sender of reaction to not be the bot
    if user != bot.user:
      #Checking for sender of event-add
      try:
        if eventaddauthors[message.id][0] == user.id:

          if str(payload.emoji) == "✅":
            eventid = int(eventaddauthors[message.id][1])

            con = sqlite3.connect("discordbotevent.db")
            cur = con.cursor()
            cur.execute("DELETE FROM events WHERE id = ?", (eventid, ))
            con.commit()
            con.close()
            logging.info(f"Deleted event {eventid} from database")

            await message.delete()
            await message.channel.send("Event deleted from database.")
            del eventaddauthors[message.id]
            logging.info(f"Removing entry from eventaddauthors: {message.id}")
            return

          elif str(payload.emoji) == "❎":

            await message.delete()
            await message.channel.send("Event not deleted.")
            logging.info("Deletion event cancelled")
            return

        else:
          await message.remove_reaction(payload.emoji, user)
          logging.info("Removing illegal reactions from eventremove message")
          return

      except KeyError:
        logging.warning("eventremove KeyError")
        await message.delete()
        await message.channel.send("Error. Try again.")
        return

  #EVENTADD REACTIONS
  if message.content.startswith("```\nADDING EVENT"):
    logging.info("reaction added to eventadd message")
    checkemoji = [emojis[i] for i in range(9, 11)]

    #Checking existing emojis are legal
    for r in message.reactions:
      if str(r) not in checkemoji:
        logging.info("Removing illegal reactions from eventadd message")
        await message.remove_reaction(r, user)

    #Checking for sender of reaction to not be the bot
    if user != bot.user:
      #Checking for sender of event-add
      try:
        if eventaddauthors[message.id][0] == user.id:
          if str(payload.emoji) == "✅":

            date = eventaddauthors[message.id][1]
            dt_obj = datetime.datetime.strptime(str(date), '%Y-%m-%d %H:%M:%S')
            ms = int(dt_obj.timestamp() * 1000)

            event = eventaddauthors[message.id][2]
            location = eventaddauthors[message.id][3]

            con = sqlite3.connect("discordbotevent.db")
            cur = con.cursor()
            cur.execute(
              "SELECT * FROM events WHERE date = ? ORDER BY date ASC LIMIT 15",
              (ms, ))
            check = cur.fetchall()

            if len(check) > 0:
              await message.delete()
              reply = "```Event is not added\nReason: Event will clash with the following:\n\n"
              for row in check:
                reply += "Id: " + str(row[0]) + "\n"
                reply += "Event: " + row[1].title() + "\n"
                reply += "Location: " + row[2].title() + "\n"
                reply += "Date: " + str(
                  datetime.datetime.fromtimestamp(row[3] / 1000.0)) + "\n"
                reply += "\n"
              reply += "```"
              await message.channel.send(reply)
              con.close()
              logging.warning("New event not added due to clash")
              return

            else:
              cur.execute(
                "INSERT INTO events (event, location, date) VALUES (?,?,?)",
                (event, location, ms))
              con.commit()
              con.close()
              await message.delete()
              await message.channel.send("Event added to database.")
              print(str(datetime.datetime.now()) + " New event added")
              del eventaddauthors[message.id]
              logging.info(
                f"Removing entry from eventaddauthors: {message.id}")
              return

          elif str(payload.emoji) == "❎":
            await message.delete()
            await message.channel.send("Event not added.")
            logging.info("New event not added")
            return

        else:
          await message.remove_reaction(payload.emoji, user)
          logging.info("Removing illegal reactions from eventadd message")
          return

      except KeyError:
        print("KeyError")
        await message.delete()
        await message.channel.send("Error. Try again.")
        logging.warning("eventadd KeyError")
        return

    else:
      return

  else:
    return


#MANAGING REACTION REMOVE
@bot.event
async def on_raw_reaction_remove(payload):

  logging.info("Reaction removed from poll message")
  counts = []
  channel = bot.get_channel(payload.channel_id)
  message = await channel.fetch_message(payload.message_id)

  #Ensure only on bot's message
  if message.author != bot.user:
    return

  #POLL REACTIONS
  if message.content.startswith("```\nPOLL"):
    numoptions = len(
      [m.span()[1] for m in re.finditer("Vote: ", message.content)])
    checkemoji = [emojis[i] for i in range(numoptions)]

    user = await bot.fetch_user(payload.user_id)

    #Checking existing emojis are legal
    for r in message.reactions:
      logging.info("Removing illegal reactions from poll message")
      if str(r) not in checkemoji:
        await message.remove_reaction(r, user)

    #Counting number of votes using reactions
    for r in message.reactions:
      counts.append(r.count - 1)

    #Updating message with votes
    text = message.content
    voteref = [m.span()[1] for m in re.finditer("Vote: ", text)]
    for i in reversed(range(len(voteref))):
      text = text[:voteref[i]] + str(counts[i]) + text[voteref[i] + 1:]
    await message.edit(content=text)


#SLASH COMMANDS
@bot.event
async def on_message(message):
  if message.author == bot.user:
    return
  sender = message.author
  await bot.process_commands(message)
  reply = ""

  #fun RE patterns xd
  text = message.content
  sender = message.author
  text = text.lower()

  if re.search("(^i[ ]{0,1}[a]{0,1}m | i[ ]{0,1}[a]{0,1}m )",
               text) is not None:
    logging.info(f"Sending Im message from {sender}")
    i = re.search("(^i[ ]{0,1}[a]{0,1}m | i[ ]{0,1}[a]{0,1}m )", text)
    reply = "Hello " + text[i.end(0):]
    await message.channel.send(reply)
    return

  elif re.search("^dame[ ]{0,1}da[ ]{0,1}[m,n]e", text) is not None:
    await message.channel.send("dame yo dame na no yo")
    return

  elif re.search("la[ ]{0,1}hee[?]{0,1}", text) is not None:
    await message.channel.send("https://www.youtube.com/watch?v=aBt4zT_PBmw")
    return

  elif re.search("(thank[s]{0,1}|thank you) (anya|housekeeping)",
                 text) is not None:
    await message.channel.send("ure welcome!")
    return


#Loading API tokens from env

if __name__ == "__main__":
  my_secret = os.environ['DISCORD_API']
  bot.run(my_secret)

