Licensed under the MIT License. 

Copyright 2017 RYAN TUBBS rmtubbs@gmail.com 

===================================================================================

COZMO'S DAILY BRIEFING

This program is a modified version of Anki's Cozmo alarm clock program, which can
be found in the Cozmo SDK program examples (http://cozmosdk.anki.com/docs/downloads.html#sdk-examples). 
My version preserves the alarm clock functionality and adds a weather report function that 
queries the Wunderground API for up-to-date weather advice that Cozmo reads aloud while
displaying an icon representing the current weather. I also added code that enables Cozmo to read aloud the date. 
Both the weather report and the date-reading function are available as standalone 
programs on my GitHub profile (https://github.com/RyanTubbs). 

In order to use this program, you must obtain a free API key (a long string of 
characters that uniquely identifies your locational preferences) from Wunderground 
(https://www.wunderground.com/weather/api/) and enter your key below on line 244 
where it says, ENTER_YOUR_API_KEY_HERE. You must also enter the 
TWO_LETTER_STATE_ABBREVIATION and YOUR_CITY name. Be aware that there are several different
Data Feature options when setting up your API key, each of which will return a
different set of JSON data. This program is designed to work with the "conditions"
Data Feature; selecting a different option would require you modify the JSON variable 
settings within this program.   
