# Twitch-Bot-Interface
The application provides an interface for a custom bot  
Allowing users to set up custom commands for viewers to use, messages to be output after every nth message and show a list of all participants of the chat for the current connection to Twitch's irc.  
  
The application provides a navigatable user interface that allows users to set up either "Callable Commands" or "Random Messages".  
## Callable Commands 
allow for a user to type the name of the command into twitch's chat function and receive a response provided certain criteria is met.  
The criteria can be:  
  * A cooldown between messages  
  * A certain "User Level" the viewer must be  
    * This allows for Moderator or Broadcaster only commands  
  * If the command is "Active" and available for use by viewers  
 
### Callable Commands Formatting:
Key | Output
---|------
t% | The word/name following the command, if there is no word the channel name
T% | The capitalised work/name following the command, if there is no word, the channel name
v% | The command caller's (message sender's) name
V% | The command caller's (message sender's) capitalised name
rv% | A random chatter's name from the viewer list
RV% | A random chatter's capitalised name from the viewer list

## Random Messages 
allow for an output into the chat upon every nth message received  
These messages do not have incredibly flexible settings  
  * They can be turned on/off, either individually or all together  
  * They can be set to iterate instead of randomise so that the messages will not repeat by accident  
  * The nth number is changeable  
  
The settings for both Random Messages and Callable Commands are asyncronous and so they can be changed whilst the bot is in use.  
For example:  
  * The random messages can be turned off for 10 messages and then turned back on. This will prevent the bot from counting these messages and so delaying the output.  
  * The number of messages required before a random message is output can be changed.  
  
Other settings such as oauth, nick, and channel need to be set up before the bot is connected otherwise it will refuse to connect.  
These can be adjusted whilst the bot is connected but will not affect the bot's ability to connect until the next attempt to start a connection  
The settings for the bot and commands save upon exit of the application and will be remembered for the next use.  

## Current Limitations:
* Moderators have to be entered manually into the code.  
* There is no built in API access which would allow live data to be retrieved from Twitch  
* Only one bot "profile" is available and so values must be changed if it is to be used on another channel.  
* Duplicate command names can not be in use, therefore you are unable to have two commands that share the name "!so" and have two different outputs based on this.  
  * In future updates this may be changed to have the Callable Commands work off a listed system instead of a dictionary, this would allow multiple commands to be used, ones that pertain to the viewers user level to be prioritised and an output be based off these criteria.  

### New Updates:
None
