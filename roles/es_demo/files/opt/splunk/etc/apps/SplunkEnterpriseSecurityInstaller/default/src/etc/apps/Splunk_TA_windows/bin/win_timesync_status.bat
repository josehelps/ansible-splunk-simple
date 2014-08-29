@echo off
REM --------------------------------------------------------
REM Copyright (C) 2005-2013 Splunk Inc. All Rights Reserved.
REM --------------------------------------------------------

setlocal EnableDelayedExpansion

REM Get the last current time synchronization status
REM
REM Example:
REM
REM     Successful sync:
REM         Last Successful Sync Time: 1/22/2014 12:06:43 PM
REM     Unsuccessful sync:
REM         Last Successful Sync Time: unspecified

REM Get the date & time
set date_time=%date% %time%

REM Print the date and time. This will be the timestamp of the event.
echo Current time: %date_time% 

REM Print the Windows time service status
w32tm /query /status /verbose

REM Print the time zone
w32tm /tz