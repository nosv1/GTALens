**Manufacturer Logos**  
Only top 50 included given discord limitations of 50 emojis per server (bots get to use server emotes anywhere, but I didn't feel like making > 1 server for this)

**Start Here**
```
python -m venv venv  
.\venv\Scripts\activate.bat  
pip install -r requirements.txt

git clone https://github.com/Rapptz/discord.py  
python -m pip install -U discord.py/.[voice]
rmdir /S discord.py
```
 
```
EDIT difflib.get_close_matches
 
    for x in possibilities TO 
    for i, x in enumerate(possibilities)
    
    AND
    
    result.append((s.ratio(), x)) TO
    result.append((s.ratio(), i))
```  