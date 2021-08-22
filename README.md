  
## Start Here  
the bot is hosted on an rPi4 but tested on Windows  
this is a note to self... obviously, you'd need the token to run the bot, and the 'Secrets' folder that is referenced in some files.
```bash
python -m venv venv  
.\venv\Scripts\activate.bat  
pip install -r requirements.txt

git clone https://github.com/Rapptz/discord.py  
python -m pip install -U discord.py/.[voice]
rmdir /S discord.py 
```

_Using Tor for scraping to avoid request limits_  
#### Windows  Setup
https://www.torproject.org/download/ for Windows  
add tor to the PATH  
tor --service install -options ControlPort 9051 SocksPort ip:9050 | more

#### Linux Setup
```bash
sudo apt-get install tor
sudo nano /etc/tor/torrc
    # edit/uncomment 
      # SocksPort ip:9050, ControlPort 9051, HashedControlPortPassword
        # sudo tor --hash-password password (copy result, paste in torrc)
    sudo service tor restart
    
```

  
## Showcase 

![](https://github.com/nosv1/GTALens/blob/dev/Showcase/track.png)  
![](https://github.com/nosv1/GTALens/blob/dev/Showcase/creator.png)  
![](https://github.com/nosv1/GTALens/blob/dev/Showcase/car.png)  
![](https://github.com/nosv1/GTALens/blob/dev/Showcase/tier.png)  
![](https://github.com/nosv1/GTALens/blob/dev/Showcase/weather.png)  
![](https://github.com/nosv1/GTALens/blob/dev/Showcase/future%20weather.png)  


## Links
#### Donate
https://ko-fi.com/gtalens

#### Invite
https://discord.com/api/oauth2/authorize?client_id=872899427457716234&permissions=36507577408&scope=bot

#### Join the server
https://discord.gg/xvsTZNefm5

#### Visit the website
https://gtalens.com/


## Notes
Only top 47 manufacturer included given discord limitations of 50 emojis per server (3 for platform logos, and bots get to use server emotes anywhere, but I didn't feel like making > 1 server for this)

