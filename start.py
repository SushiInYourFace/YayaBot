import logging
import subprocess
import sys

logging.basicConfig(format='[%(asctime)s] %(levelname)s: %(message)s', level=logging.INFO)

# IF YOU ARE EDITING THIS: make sure the script is compatable with lower versions of python (this means no fstrings)

if not (sys.version_info[0] >= 3 and sys.version_info[1] >= 8):
    logging.warning("Python version 3.8+ is required, you are running this with " + ".".join([str(i) for i in sys.version_info[:3]]))
    exit()

pip = True

try:
    import pkg_resources
except:
    logging.warning("pip is not installed. Continuing without requirements check.")
    pip = False

run = True

def requirements_check():
    try:
        pkg_resources.require(open('requirements.txt',mode='r'))
    except pkg_resources.DistributionNotFound as error:
        logging.warning(str(error)+"! Run '"+sys.executable+" -m pip install -r requirements.txt' as admin/sudo or with '--user'. Press ctrl+c to stop or press enter to continue anyway.")
        input()

while run:
    subprocess.run(["git","fetch","origin"])
    b = subprocess.Popen(["git", "rev-parse", "--abbrev-ref", "HEAD"],stdout=subprocess.PIPE)
    branch = b.communicate()[0].decode().replace("\n","")
    local = subprocess.Popen(["git", "log", "--name-only", "origin/"+branch+"..HEAD"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = local.communicate()
    if not out:
        incoming = subprocess.Popen(["git", "diff", "--name-only", "HEAD", "origin/"+branch], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = incoming.communicate()
        if out:
            subprocess.run(["git", "pull"], stdout=subprocess.PIPE)
            logging.info("Updated!")
        else:
            logging.info("No Update Required.")
    else:
        logging.info("Committed changes, not updating.")
    if pip:
        requirements_check()
    code = subprocess.run([sys.executable,"bot.py"],stdout=subprocess.PIPE).returncod
    if code == 0:
        run = False

logging.info("Shutting Down")
