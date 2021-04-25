import subprocess
import sys
import logging

logging.basicConfig(format='[%(asctime)s] %(levelname)s: %(message)s', level=logging.INFO)

run = True

while run:
    subprocess.run(["git","fetch","origin"])
    b = subprocess.Popen(["git", "rev-parse", "--abbrev-ref", "HEAD"],stdout=subprocess.PIPE)
    branch = b.communicate()[0].decode().replace("\n","")
    local = subprocess.Popen(["git", "log", "--name-only", f"origin/{branch}..HEAD"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = local.communicate()
    if not out:
        incoming = subprocess.Popen(["git", "diff", "--name-only", "HEAD", f"origin/{branch}"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = incoming.communicate()
        if out:
            subprocess.run(["git", "pull"], stdout=subprocess.PIPE)
            logging.info("Updated!")
        else:
            logging.info("No Update Required.")
    else:
        logging.info("Committed changes, not updating.")
    code = subprocess.run([sys.executable,"bot.py"],stdout=subprocess.PIPE).returncode
    if code == 0:
        run = False

logging.info("Shutting Down")