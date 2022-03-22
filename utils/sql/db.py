import datetime
import gzip
import os
import shutil
import sqlite3

class backups:
    async def make_backup(connection, kept_backups):
        """Creates a backup file of the current SQL database"""
        backup = sqlite3.connect("resources/backups/tempbackupfile.db")
        with backup:
            await connection.backup(backup, pages=1) #actual backup happens here
        backup.close()
        timestamp = datetime.datetime.now().strftime('%m_%d_%Y-%H_%M_%S')
        fname = f'resources/backups/{timestamp}.db.gz'
        with gzip.open(fname, 'wb') as f_out:
            with open("resources/backups/tempbackupfile.db", "rb") as f_in:
                shutil.copyfileobj(f_in, f_out)
        os.remove("resources/backups/tempbackupfile.db")
        if kept_backups != 0:
            #list of all files except gitkeep, sorted chronologically
            files = sorted([f for f in os.listdir('resources/backups') if os.path.isfile(os.path.join('resources/backups',f)) and f != ".gitkeep"])
            while len(files) > kept_backups:
                oldest_file = files[0]
                os.remove(f"resources/backups/{oldest_file}")
                files = sorted([f for f in os.listdir('resources/backups') if os.path.isfile(os.path.join('resources/backups',f)) and f != ".gitkeep"])