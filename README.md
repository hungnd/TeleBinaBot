# TeleBinaBot

### Install
Install system lib `apt install libgl1 tesseract-ocr libtesseract-dev`
Install python lib `pip3 install requests telethon opencv-python==4.6.0.66 pytesseract`

### Diagnostic

#### Sync time server
`sudo service ntp stop`
`sudo ntpdate -s time.nist.gov`
`sudo service ntp start`
