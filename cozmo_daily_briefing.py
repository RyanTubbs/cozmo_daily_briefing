#!/usr/bin/env python3

# Licensed under the MIT License. 
#
# Copyright 2017 RYAN TUBBS rmtubbs@gmail.com 
#
# Permission is hereby granted, free of charge, to any person obtaining 
# a copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is 
# furnished to do so, subject to the following conditions: 
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software. 
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A 
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE 
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE. 

# This program is a modified version of Anki's Cozmo alarm clock program, which can
# be found in the Cozmo SDK program examples (http://cozmosdk.anki.com/docs/downloads.html#sdk-examples). 
# My version preserves the alarm clock functionality and adds a weather report function that 
# queries the Wunderground API for up-to-date weather advice that Cozmo reads aloud while
# displaying an icon representing the current weather. I also added code that enables Cozmo to read aloud the date. 
# Both the weather report and the date-reading function are available as standalone 
# programs on my GitHub profile (https://github.com/RyanTubbs). 

# In order to use this program, you must obtain a free API key (a long string of 
# characters that uniquely identifies your locational preferences) from Wunderground 
# (https://www.wunderground.com/weather/api/) and enter your key below on line 244 
# where it says, ENTER_YOUR_API_KEY_HERE. You must also enter the 
# TWO_LETTER_STATE_ABBREVIATION and YOUR_CITY name. Be aware that there are several different
# Data Feature options when setting up your API key, each of which will return a
# different set of JSON data. This program is designed to work with the "conditions"
# Data Feature; selecting a different option would require you modify the JSON variable 
# settings within this program.    

import datetime #Imports the Python 'datetime' module, which enables this program to work with date & time-related data.
import math #Imports the Python 'math' module, which enables this program to calculate the position of the clock hands.   
import sys #Imports the Python 'sys' module, allowing the interpreter to use certain variables.  
import time #Imports the Python 'time' module for additional time-related functionality. 
import cozmo #Imports the 'cozmo' module from Cozmo's API, which enables this program to access Cozmo's core capabilities.
import urllib.request #Imports the Python 'urllib.request' module so the program can open the API URL. 
import json #Imports the Python 'json' module so the program can interpret the JSON data received from Wunderground. 
import requests #Imports Kenneth Reitz's 'requests' module for Python. It's similar to 'urllib.request', but offers higher-level functionality. 
from io import BytesIO #Imports the Python 'BytesIO' module to interpret binary data from the weather conditions icon.  
try:
    from PIL import Image, ImageDraw, ImageFont #Imports various Pillow modules to help display images on Cozmo's face. 
except ImportError: #Error notification and instructions if the end user has not previously installed Pillow.
    sys.exit("Cannot import from PIL. Do `pip3 install --user Pillow` to install") 

#: bool: Set to True to display the clock as analog
#: (with a small digital readout below)
SHOW_ANALOG_CLOCK = False

def make_text_image(text_to_draw, x, y, font=None):
    '''Make a PIL.Image with the given text printed on it

    Args:
        text_to_draw (string): the text to draw to the image
        x (int): x pixel location
        y (int): y pixel location
        font (PIL.ImageFont): the font to use

    Returns:
        :class:(`PIL.Image.Image`): a PIL image with the text drawn on it
    '''

    # make a blank image for the text, initialized to opaque black
    text_image = Image.new('RGBA', cozmo.oled_face.dimensions(), (0, 0, 0, 255))

    # get a drawing context
    dc = ImageDraw.Draw(text_image)

    # draw the text
    dc.text((x, y), text_to_draw, fill=(255, 255, 255, 255), font=font)

    return text_image

# get a font - location depends on OS so try a couple of options
# failing that the default of None will just use a default font
_clock_font = None
try:
    _clock_font = ImageFont.truetype("arial.ttf", 20)
except IOError:
    try:
        _clock_font = ImageFont.truetype("/Library/Fonts/Arial.ttf", 20)
    except IOError:
        pass

def draw_clock_hand(dc, cen_x, cen_y, circle_ratio, hand_length):
    '''Draw a single clock hand (hours, minutes or seconds)

    Args:
        dc: (:class:`PIL.ImageDraw.ImageDraw`): drawing context to use
        cen_x (float): x coordinate of center of hand
        cen_y (float): y coordinate of center of hand
        circle_ratio (float): ratio (from 0.0 to 1.0) that hand has travelled
        hand_length (float): the length of the hand
    '''

    hand_angle = circle_ratio * math.pi * 2.0
    vec_x = hand_length * math.sin(hand_angle)
    vec_y = -hand_length * math.cos(hand_angle)

    # x_scalar doubles the x size to compensate for the interlacing
    # in y that would otherwise make the screen appear 2x tall
    x_scalar = 2.0

    # pointy end of hand
    hand_end_x = int(cen_x + (x_scalar * vec_x))
    hand_end_y = int(cen_y + vec_y)

    # 2 points, perpendicular to the direction of the hand,
    # to give a triangle with some width
    hand_width_ratio = 0.1
    hand_end_x2 = int(cen_x - ((x_scalar * vec_y) * hand_width_ratio))
    hand_end_y2 = int(cen_y + (vec_x * hand_width_ratio))
    hand_end_x3 = int(cen_x + ((x_scalar * vec_y) * hand_width_ratio))
    hand_end_y3 = int(cen_y - (vec_x * hand_width_ratio))

    dc.polygon([(hand_end_x, hand_end_y), (hand_end_x2, hand_end_y2),
                (hand_end_x3, hand_end_y3)], fill=(255, 255, 255, 255))

def make_clock_image(current_time):
    '''Make a PIL.Image with the current time displayed on it

    Args:
        text_to_draw (:class:`datetime.time`): the time to display

    Returns:
        :class:(`PIL.Image.Image`): a PIL image with the time displayed on it
    '''

    time_text = time.strftime("%I:%M:%S %p")

    if not SHOW_ANALOG_CLOCK:
        return make_text_image(time_text, 8, 6, _clock_font)

    # make a blank image for the text, initialized to opaque black
    clock_image = Image.new('RGBA', cozmo.oled_face.dimensions(), (0, 0, 0, 255))

    # get a drawing context
    dc = ImageDraw.Draw(clock_image)

    # calculate position of clock elements
    text_height = 9
    screen_width, screen_height = cozmo.oled_face.dimensions()
    analog_width = screen_width
    analog_height = screen_height - text_height
    cen_x = analog_width * 0.5
    cen_y = analog_height * 0.5

    # calculate size of clock hands
    sec_hand_length = (analog_width if (analog_width < analog_height) else analog_height) * 0.5
    min_hand_length = 0.85 * sec_hand_length
    hour_hand_length = 0.7 * sec_hand_length

    # calculate rotation for each hand
    sec_ratio = current_time.second / 60.0
    min_ratio = (current_time.minute + sec_ratio) / 60.0
    hour_ratio = (current_time.hour + min_ratio) / 12.0

    # draw the clock hands
    draw_clock_hand(dc, cen_x, cen_y, hour_ratio, hour_hand_length)
    draw_clock_hand(dc, cen_x, cen_y, min_ratio, min_hand_length)
    draw_clock_hand(dc, cen_x, cen_y, sec_ratio, sec_hand_length)

    # draw the digital time_text at the bottom
    x = 32
    y = screen_height - text_height
    dc.text((x, y), time_text, fill=(255, 255, 255, 255), font=None)

    return clock_image

def convert_to_time_int(in_value, time_unit):
    '''Convert in_value to an int and ensure it is in the valid range for that time unit

    (e.g. 0..23 for hours)'''

    max_for_time_unit = {'hours': 23, 'minutes': 59, 'seconds': 59}
    max_val = max_for_time_unit[time_unit]

    try:
        int_val = int(in_value)
    except ValueError:
        raise ValueError("%s value '%s' is not an int" % (time_unit, in_value))

    if int_val < 0:
        raise ValueError("%s value %s is negative" % (time_unit, int_val))

    if int_val > max_val:
        raise ValueError("%s value %s exceeded %s" % (time_unit, int_val, max_val))

    return int_val


def extract_time_from_args():
    ''' Extract a (24-hour-clock) user-specified time from the command-line

    Supports colon and space separators - e.g. all 3 of "11 22 33", "11:22:33" and "11 22:33"
    would map to the same time.
    The seconds value is optional and defaults to 0 if not provided.'''

    # split sys.argv further for any args that contain a ":"
    split_time_args = []
    for i in range(1, len(sys.argv)):
        arg = sys.argv[i]
        split_args = arg.split(':')
        for split_arg in split_args:
            split_time_args.append(split_arg)

    if len(split_time_args) >= 2:
        try:
            hours = convert_to_time_int(split_time_args[0], 'hours')
            minutes = convert_to_time_int(split_time_args[1], 'minutes')
            seconds = 0
            if len(split_time_args) >= 3:
                seconds = convert_to_time_int(split_time_args[2], 'seconds')

            return datetime.time(hours, minutes, seconds)
        except ValueError as e:
            print("ValueError %s" % e)

    # Default to no alarm
    return None


def get_in_position(robot: cozmo.robot.Robot):
    '''If necessary, Move Cozmo's Head and Lift to make it easy to see Cozmo's face'''
    if (robot.lift_height.distance_mm > 45) or (robot.head_angle.degrees < 40):
        with robot.perform_off_charger():
            robot.set_lift_height(0.0).wait_for_completed()
            robot.set_head_angle(cozmo.robot.MAX_HEAD_ANGLE).wait_for_completed()

def weather_advice(robot: cozmo.robot.Robot):
    #This is the weather report portion of the program; it contains the API request, JSON conversion, and image processing,
    #allowing Cozmo to read the weather report and display the weather icon.      
              
    with urllib.request.urlopen("http://api.wunderground.com/api/ENTER_YOUR_API_KEY_HERE/geolookup/conditions/q/TWO_LETTER_STATE_ABBREVIATION/YOUR_CITY.json") as url: 
    #This line includes the actual API call to Wunderground's server using the 'urllib.request' module. If you paste this URL into 
    #your browser, you should be able to see the raw, nested JSON data, which is helpful for understanding where we pull our data from
    #in the variables we declare below. Be sure to customize the URL with your API key, two-letter state abbreviation, and city name!   

        parsed_json = json.loads(url.read().decode()) 
        #We now take the received JSON data and convert it into a format we can utilize in Python by using the .loads, .read, and 
        #.decode methods from the 'json' module. We also place this converted data into a variable named 'parsed_json' so we can  
        #manipulate this data in the lines that follow.

        temp_f = parsed_json['current_observation']['temp_f'] 
        #We declare another variable named 'temp_f' that pulls the current temperature from the nested data we just converted above.
        #This variable returns an integer, which Cozmo cannot speak aloud, but he utilizes it as a parameter within the program.  

        temperature = str(parsed_json['current_observation']['temp_f'])
        #This variable accesses the same data as the 'temp_f' variable, but here we convert it to a string (words/text) using the str method 
        #so that Cozmo can say the temperature aloud. 

        weather = parsed_json['current_observation']['weather'] 
        #Another variable like the one above, but this time returning a short string describing the general weather conditions. These data are 
        #already in the form of a string, so Cozmo can speak this without converting it with str.  

        wind = parsed_json['current_observation']['wind_string']
        #Another variable string, this time describing the wind conditions. 

        icon = parsed_json['current_observation']['icon_url']
        #This variable pulls the URL for the icon that represents the current weather conditions from our nested data. 

        r = requests.get(icon)
        #Now we create a variable that uses the .get method from the 'requests' module to access the icon URL, 
        #which we get by calling the 'icon' variable we just created above. 

        image = Image.open(BytesIO(r.content))
        #The next step is to convert the binary data into an image using 'BytesIO' and open it using the 'Image' module; we set this result as
        #an 'image' variable.  
        
        resized_image = image.resize(cozmo.oled_face.dimensions(), Image.BICUBIC) 
        #We call our 'image' variable and make it fit Cozmo's screen using the .resize method from the 'cozmo' module. 

        face_image = cozmo.oled_face.convert_image_to_screen_data(resized_image, invert_image=True, pixel_threshold=175) 
        #We finally have an icon image that will display on Cozmo's screen! The invert_image parameter displays the icon as an outline on a black
        #screen. A pixel_threshold of around 175 seems to display the icon cleanly; the default pixel_threshold of 127 will not display the image.

        action1 = robot.say_text("Right now the weather is " + weather + "." + "The wind is " + wind + "." 
            +  "The temperature is currently " + temperature + "degrees Fahrenheit.") 
        #Now we're almost ready for action! We use Cozmo's .say_text method to assemble a variable string for Cozmo to speak. We combine text  
        #(within quotations) with the strings from our 'weather', 'wind', and 'temperature' variables to produce the three sentences that make 
        #up the weather report.

        action2 = robot.display_oled_face_image(face_image, 5000.0)
        #We create a variable that tells Cozmo to display the 'face_image' variable on his screen for 5000 milliseconds which, unsurprisingly, 
        #works out to 5 seconds. One of the default parameters for this method is in_parallel=True, which allows the image to display on Cozmo's
        #face while he speaks, rather than waiting until he's done.  

        action1.wait_for_completed()
        #Tells the program to wait until 'action1' is done before proceeding. 

        action2.wait_for_completed()
        #Tells the program to wait until 'action2' is done before proceeding. 
        
        if temp_f < 40:
            robot.say_text("It is cold outside right now. You should wear a jacket to prevent system failure!").wait_for_completed()
        if 40 <= temp_f < 60:
            robot.say_text("It is cool outside right now. You might want a sweater to maintain proper operating temperature.").wait_for_completed()
        if 60 <= temp_f <= 80:
            robot.say_text("It is a comfortable temperature for humans outside right now.").wait_for_completed()
        if temp_f > 80:
            robot.say_text("It's pretty hot right now. Don't overheat your circuits!").wait_for_completed()
        #Lastly, we use a series of if statements, our 'temp_f' variable, and some comparison operators to create four different phrases that Cozmo
        #speaks depending on the current temperature.  

def alarm_clock(robot: cozmo.robot.Robot):
    '''The core of the alarm_clock program'''

    alarm_time = extract_time_from_args()
    if alarm_time:
        print("Alarm set for %s" % alarm_time)
    else:
        print("No Alarm time provided. Usage example: 'alarm_clock.py 17:23' to set alarm for 5:23 PM. (Input uses the 24-hour clock.)")
    print("Press CTRL-C to quit")

    get_in_position(robot)

    was_before_alarm_time = False
    last_displayed_time = None

    while True:
        # Check the current time, and see if it's time to play the alarm

        current_time = datetime.datetime.now().time()

        do_alarm = False
        if alarm_time:
            is_before_alarm_time = current_time < alarm_time
            do_alarm = was_before_alarm_time and not is_before_alarm_time  # did we just cross the alarm time
            was_before_alarm_time = is_before_alarm_time

        if do_alarm:
            # Cancel the latest image display action so that the alarm actions can play
            robot.abort_all_actions()
            # Speak The Time (off the charger as it's an animation)
            with robot.perform_off_charger():
                short_time_string = str(current_time.hour) + ":" + str(current_time.minute)

                day_month = datetime.datetime.now().strftime('%A'+', '+'%B'+' '+'%d' + ', ' + '%Y')
                #The line above defines the 'date' variable as a text string in the format of "Weekday, Month Date, Year". 
                #Additional date (and time) formats can be constructed by changing the %variables within the parentheses. 
                #See https://docs.python.org/2/library/datetime.html#strftime-and-strptime-behavior for a listing of available variables.

                robot.say_text("Attention, Human! It's " + short_time_string).wait_for_completed()
                robot.say_text("Human, listen up and get ready for your daily briefing! Here it comes at " + short_time_string).wait_for_completed()
                robot.say_text("Today is " + day_month).wait_for_completed()

                weather_advice(robot)
                #This line calls the 'weather_advice' function defined above.  

        else:

            # See if the displayed time needs updating

            if (last_displayed_time is None) or (current_time.second != last_displayed_time.second):
                # Create the updated image with this time
                clock_image = make_clock_image(current_time)
                oled_face_data = cozmo.oled_face.convert_image_to_screen_data(clock_image)

                # display for 1 second
                robot.display_oled_face_image(oled_face_data, 1000.0)
                last_displayed_time = current_time

        # only sleep for a fraction of a second to ensure we update the seconds as soon as they change
        time.sleep(0.1)
   
cozmo.robot.Robot.drive_off_charger_on_connect = False  # Cozmo can stay on his charger for this example

cozmo.run_program(alarm_clock)
#Finally, we execute the entire program, including the alarm clock and weather report.



 






