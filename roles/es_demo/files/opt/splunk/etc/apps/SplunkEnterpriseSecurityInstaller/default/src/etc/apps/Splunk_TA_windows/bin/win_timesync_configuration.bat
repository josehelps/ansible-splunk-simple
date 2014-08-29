@echo off
REM --------------------------------------------------------
REM Copyright (C) 2005-2013 Splunk Inc. All Rights Reserved.
REM --------------------------------------------------------

setlocal EnableDelayedExpansion

REM Get the time service configuration and timezone.

REM Get the date & time
set date_time=%date% %time%

REM Print the date and time. This will be the timestamp of the event.
echo Current time: %date_time% 

REM Print the Windows time service configuration
w32tm /query /configuration /verbose

REM Print the Windows time zone information
w32tm /tz