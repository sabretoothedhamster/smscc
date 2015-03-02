#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# SMS Control Center v0.1
# (C)reated by MaxWolf 2015
# Distributed under GPL, see https://gnu.org/licenses/gpl.html for details
# $Id$
#
import os, sys, shutil, subprocess, re, getopt, logging, ConfigParser, fnmatch

def print_err(*args):
    sys.stderr.write(' '.join(map(str,args)) + '\n')

##################################################################
#
#

class SMSCconfig:
    def __init__(self):
    	# some reasonable defaults
        self.inMsgs = "/var/pool/gammu/inbox"
        self.inArc = "/var/spool/gammu/inbox-processed"
        self.sendCmd = "gammu-smsd-inject TEXT $N -unicode -len $L -text $T"
        self.clients = {}
        self.resources = {}
        self.groups = {}

    def load(self, cfgFileName):
        try:
            config = ConfigParser.SafeConfigParser()
            config.optionxform = str
            loaded = config.read([cfgFileName, os.path.expanduser("~/" + cfgFileName), "/etc/" + cfgFileName])
            if len(loaded) == 0:
                logging.critical("Can not load configuration file '%s'" % cfgFileName)
                return False

            sn = "general"
#            if config.has_option(sn, "log"):
#                self.logFile = config.get(sn, "log")
#            if logFileName != "":
#                self.logFile = logFileName

            if config.has_option(sn, "in"):
                self.inMsgs = config.get(sn, "in")
            if config.has_option(sn, "inArc"):
                self.inArc = config.get(sn, "inArc")
            if config.has_option(sn, "sendCmd"):
                self.sendCmd = config.get(sn, "sendCmd")

            if not os.path.isdir(self.inMsgs):
                logging.critical("Directory %s does not exist" % self.inMsgs)
                return False
            if not os.path.isdir(self.inArc):
                os.makedirs(self.inArc)


            sn = "clients"
            for phn, ar in config.items(sn):
                self.clients[phn] = ar

            sn = "resources"
            for rname, rvalue in config.items(sn):
                if not self.parse_resource(rname, rvalue):
                    return False

            sn = "groups"
            for gname, gvalue in config.items(sn):
                self.groups[gname] = gvalue

            return True

        except ConfigParser.Error, err:
            logging.critical("Cannot parse configuration file. %s" %err)
            return False
        except (IOError, Exception), err:
            logging.critical("Problem opening configuration file. %s" %err)
            return False
        except:
            logging.critical("Unexpected error:", sys.exc_info()[0])
            return False

    def parse_resource(self, rname, rvalue):
#        logging.debug("Resource=%s/%s" %(rname, rvalue))
        rlist = rvalue.split(";")
        if len(rlist) != 4:
            logging.critical("Invalid resource %s definition" %rname)
            return False
        self.resources[rname] = {}
        self.resources[rname]["descr"] = rlist[0]
        self.resources[rname]["ar"] = rlist[1]
        self.resources[rname]["getter"] = rlist[2]
        self.resources[rname]["setter"] = rlist[3]
#        logging.debug("Resource %s parsed [%s][%s][%s]", rname, self.resources[rname]["descr"], self.resources[rname]["getter"], self.resources[rname]["setter"])
        return True




##################################################################
#
# SMS processing
# 
def append_sms_to_list(smsList, sms):
    if sms["partN"] != "00":
        for s in reversed(smsList):
            logging.debug("  Comparing to %s part %s (%d)" %(s["cid"], s["partN"], s["lastPartN"]))
            if (s["partN"] == "00") and (s["cid"] == sms["cid"]) and (s["lastPartN"] + 1 == int(sms["partN"])):
                logging.debug("Merging SMS file %s to %s" %(sms["fnames"][0], s["fnames"][0]))
                s["lastPartN"] += 1
                s["text"] += sms["text"]
                s["fnames"].append(sms["fnames"][0])
                return

    sms["lastPartN"] = 0
    smsList.append(sms)
    logging.debug("SMS file %s appended" %sms["fnames"][0])
    return


def scan_for_sms(cfg):
    logging.debug("=== Scanning %s for new SMSes" %cfg.inMsgs)
    dirList = os.listdir(cfg.inMsgs)
    smsList = []
    for fn in dirList:
        logging.info("Found file %s" %fn)
        sms = {}
        try:
            nparts = fn.split("_")
            mpref = nparts[0][0:2]
            sms["date"] = nparts[0][2:]
            sms["time"] = nparts[1]
            sms["sn"] = nparts[2]
            sms["cid"] = nparts[3]
            sms["partN"] = nparts[4][0:2]
        except:
            logging.info("File %s skipped as invalid filename msg" %fn)
            shutil.move(os.path.join(cfg.inMsgs, fn), os.path.join(cfg.inArc, fn))
            continue

        logging.debug("Pref=%s, date=%s, time=%s, n1=%s, cid=%s, mpn=%s" %(mpref, sms["date"], sms["time"], sms["sn"], sms["cid"], sms["partN"]))

        if mpref != "IN":
            logging.info("File %s skipped as non-IN msg" %fn)
            shutil.move(os.path.join(cfg.inMsgs, fn), os.path.join(cfg.inArc, fn))
            continue
        if nparts[4][2:] != ".txt":
            logging.info("File %s skipped as non-txt msg" %fn)
            shutil.move(os.path.join(cfg.inMsgs, fn), os.path.join(cfg.inArc, fn))
            continue
        sms["fnames"] = []
        sms["fnames"].append(fn)
        sms["text"] = open(os.path.join(cfg.inMsgs, fn)).read()
        append_sms_to_list(smsList, sms)
        
#    for s in smsList:
#        print "SMS from %s (%s): [%s]" %(s["cid"], s["time"], s["text"])
    return check_sms(cfg, smsList)

def check_sms(cfg, smsList):
    logging.info("=== Processing %d SMSs" %len(smsList))
    for s in smsList:
#        logging.debug("SMS from %s (%s): [%s]" %(s["cid"], s["time"], s["text"]))
        for cli in cfg.clients.keys():
#            logging.debug("Matching to %s" % cli)
            if re.match(cli, s["cid"]):
                logging.info("CID %s Matched. AR=%s" %(s["cid"], cfg.clients[cli]))
                logging.info("Message text [%s]" %s["text"])
                if cfg.clients[cli][0] == ">":
                    forward_sms(cfg, s, cfg.clients[cli][1:])
                else:
                    process_sms(s, cfg.clients[cli], cfg)
                break
        else:
            logging.warning("SMS from unknown CID %s - ignored" %s["cid"])

        for fn in s["fnames"]:
            logging.info("File %s moved into processed directory" %fn)
            shutil.move(os.path.join(cfg.inMsgs, fn), os.path.join(cfg.inArc, fn))


    return 0

def forward_sms(cfg, sms, to):
    try:
        logging.info("Forwarding SMS to [%s]" %to)
        cc = re.sub("\$N", to, cfg.sendCmd)
        txt = "From " + sms["cid"] + ":" + sms["text"]
        cc = re.sub("\$T", txt, cc)
        cc = re.sub("\$L", str(len(txt) + 1), cc)
        logging.debug("SMS send cmd=[%s]" %cc)
        p = subprocess.Popen(cc, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, shell=True)
        out, err = p.communicate()
    except Exception, edescr:
        logging.error("Send SMS exception: %s" %edescr);
    else:
        logging.info("Send SMS returned out=[%s] and err=[%s]" %(out, err))
    

def filter_cmd(cmd):
    cmdout = ""
    for i in range(0, len(cmd)):
        if cmd[i].isalnum() or cmd[i] == ".":
            cmdout += cmd[i]
    return cmdout

def process_sms(sms, ar, cfg):
    if sms["text"][0] == ">":
        logging.info("Ignore service message")
        return 0
    cmds = sms["text"].split(" ")
    reply = ""
    logging.debug("There are %d cmds in SMS text [%s]" %(len(cmds), sms["text"]))
    for c in cmds:
        prm = ""
        query = (c.find("?") != -1)
        descr = (c.find("$") != -1)
        noread = (c.find("-") != -1)
        scan = (c.find("*") != -1)
        i = c.find("=")
        if i != -1:
            cname = filter_cmd(c[0:i]).upper()
            prm = filter_cmd(c[i+1:]).upper()
        else:
            cname = filter_cmd(c).upper()
        logging.debug("For cmd [%s] got cname=[%s], prm=[%s]" %(c, cname, prm))
        if scan:
            reply += process_scan(c, ar, cfg)
        elif cname in cfg.groups.keys():
            logging.info("Processing group [%s]" %cname)
            glist = cfg.groups[cname].split(",")
            for k in glist:
                reply += process_cmd(k, prm, query, descr, ar, cfg)
        elif cname in cfg.resources.keys():
            reply += process_cmd(cname, prm, query, descr, ar, cfg)
        else:
            reply += "?" + cname + ";"
            logging.warning("Unknown resource %s from cmd %s" %(cname, c))


    logging.info("Sending reply SMS to [%s]:[%s]" %(sms["cid"], reply))
    reply = ">" + reply
    try:
        cc = re.sub("\$N", sms["cid"], cfg.sendCmd)
        cc = re.sub("\$T", reply, cc)
        cc = re.sub("\$L", str(len(reply) + 1), cc)
        logging.debug("SMS send cmd=[%s]" %cc)
        p = subprocess.Popen(cc, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, shell=True)
        out, err = p.communicate()
    except Exception, edescr:
        logging.error("Send SMS exception: %s" %edescr);
    else:
        logging.info("Send SMS returned out=[%s] and err=[%s]" %(out, err))


    return 0


def has_right(ar, target):
    logging.debug("Checking [%s] for [%s]" %(ar, target))
    if len(target) == 0:
        return True
    for r in target[:]:
        logging.debug("Check [%s] in [%s]" %(r, ar))
        if ar.find(r) != -1:
            return True
    return False


def process_cmd(cname, prm, query, descr, ar, cfg):
    reply = ""
    cc = ""
    if len(prm) != 0:
        cc = cfg.resources[cname]["setter"]
        if len(cc) == 0:
            logging.error("No setter for cname %s configured" %cname)
        else:
            cc = re.sub(r"\$", prm, cc)
            logging.info("For cname %s starting setter cmd [%s]" %(cname, cc))
    elif query:
        cc = cfg.resources[cname]["getter"]
        logging.info("For cname %s starting query cmd [%s]" %(cname, cc))

    if (len(cc) == 0) or ((len(prm) == 0) and (ar.find("R") == -1)) or ((len(prm) != 0) and (ar.find("W") == -1)) or not has_right(ar, cfg.resources[cname]["ar"]):
        reply += "&" + cname + ";"
        logging.error("Permission error of [%s]" %cname)
    else:
        try:
            p = subprocess.Popen(cc, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, shell=True)
            out, err = p.communicate()
        except Exception, edescr:
            logging.error("Cmd exception: %s" %edescr);
            if descr:
                reply += "%s(%s) - failed;" % (cfg.resources[cname]["descr"], cname)
            else:
                reply += "#" + cname + ";"
        else:
            logging.info("Cmd returned out=[%s] and err=[%s]" %(out, err))
            if len(out) == 0 and len(err) != 0:
                if descr:
                    reply += "%s(%s) - error;" % (cfg.resources[cname]["descr"], cname)
                else:
                    reply += "#" + cname + ";"
            else:
                out = out.lstrip(" ?*$%#^\r\n").rstrip(" ?*$%#^\r\n")
                if descr:
                    reply += "%s(%s)=%s;" % (cfg.resources[cname]["descr"], cname, out)
                else:
                    reply += cname + "=" + out + ";"
    return reply

def process_scan(c, ar, cfg):
    reply = ""
    if ar.find("S") == -1:
        reply += "&" + c + ";"
        logging.error("Permission error of [%s]" %c)
    else:
        logging.info("Processing resources scan [%s]" %c)
        for n in cfg.groups.keys():
            if fnmatch.fnmatch(n, c):
                reply += n + ":" + cfg.groups[n] + ";"
        for n in cfg.resources.keys():
            if has_right(ar, cfg.resources[n]["ar"]) and fnmatch.fnmatch(n, c):
                reply += n + ":" + cfg.resources[n]["descr"]
                if len(cfg.resources[n]["setter"]) != 0:
                    reply += "*;"
                else:
                    reply += ";"
    return reply
        
##################################################################
#
#

def usage(progName):
    print_err(progName + ' --config=<configFile> --log=<logfile> --scan --test');


def main(argv):

    cfgFileName = "/root/smscc/smscc.conf"
    logfileName = "/var/log/smscc.log"
#    logfileName = "/maxwolf/Projects/WirenBoard/smssrv/smscc.log"

    try:
        opts, args = getopt.getopt(argv[1:],"hlcs",["log=", "config=","scan","test"])
    except getopt.GetoptError, e:
        print_err("Invalid options: " + e.msg)
        usage(argv[0])
        return 2

    scan = True
    test = False
    for opt, arg in opts:
        if opt == '-h':
            usage(argv[0])
            sys.exit(2)
        elif opt in ("-c", "--config"):
            cfgFileName = arg
        elif opt in ("-l", "--log"):
            logfileName = arg
        elif opt in ("-s", "--scan"):
            scan = 1
        elif opt in ("-t", "--test"):
            test = 1
         
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s',
        filename=logfileName, filemode='a')

    logging.info('===== Starting SMSCC. Config file is ' + cfgFileName)
    cfg = SMSCconfig()
    if not cfg.load(cfgFileName):
        return 1

    if test:
        logging.info('===== Stopping SMSCC. Config check Ok')
        return 0

    if scan == 1:
        return scan_for_sms(cfg)

    return 1

if __name__ == "__main__":
    ret = main(sys.argv)
    logging.info("===== Finished with code %d" %ret)
    exit(ret)


