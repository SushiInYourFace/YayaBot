import subprocess
import sys
import logging

logging.basicConfig(format='[%(asctime)s] %(levelname)s: %(message)s', level=logging.INFO)

run = True

while run:
    local = subprocess.Popen(["git", "fetch", "origin",";","git", "log", "--name-only", "FETCH_HEAD..HEAD"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = local.communicate()
    if not out:
        incoming = subprocess.Popen(["git", "fetch", "origin", ";", "git", "diff", "--name-only", "HEAD", "FETCH_HEAD"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = incoming.communicate()
        if out:
            subprocess.Popen("git pull", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            logging.info("Updated!")
        else:
            logging.info("No Update Required.")
    else:
        logging.info("Committed changes, not updating.")
    code = subprocess.run([sys.executable,"bot.py"],stdout=subprocess.PIPE)
    if code == 0:
        run = False
