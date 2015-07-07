#!/usr/bin/env python3
# encoding: utf-8

import time
import os
import logging
import re

from configparser import ConfigParser
from datetime import datetime

from pyvirtualdisplay import Display
from selenium import webdriver
from PIL import Image

DISPLAY = False
DEFAULT_SAVE_PATH = "weeklys"
MAX_MEMBER_IN_ONE_IMAGE = 20 # the number of screenshots merged into a picture
GROUP_FILTER_LIST = ["总经办", "CrossOver 援兵", "江南援兵", "合作伙伴"] # will not count the user in this group
EMAIL_FILTER_LIST = ["weeky_reports_robot@linuxdeepin.com"] # will not count the user in this list
LOG_FILE = "WeeklyRobot.log"
CONFIG_FILE = "TowerWeeklyRobot.ini" if os.path.exists("TowerWeeklyRobot.ini") else\
        os.path.join(os.getenv("HOME"), ".AutoScriptConfig/TowerWeeklyRobot.ini")

logging.basicConfig(level=logging.DEBUG, filename=LOG_FILE, format="%(asctime)s - %(levelname)s - %(message)s")


# test function
def saveWebScreenshot(url, savePath):

    display = Display(visible=0, size=(1366, 768))
    display.start()

    browser = webdriver.Firefox()
    browser.get(url)
    browser.save_screenshot(savePath)
    browser.quit()

    display.stop()


def getTowerWeeklyScreenshot(username, passwd, savePath):

    projectUrl = "https://tower.im/teams/0/projects/"
    browser = webdriver.Firefox()
    browser.get(projectUrl)

    # ready dirs
    now = datetime.now()
    dateStr = "%d-%d-%d" %(now.year, now.month, now.day)
    datePath = "%s/%s" % (savePath, dateStr)
    membersPath = "%s/members" %(datePath)
    os.makedirs(membersPath, exist_ok=True)

    # login
    logging.debug("login ...")
    print ("login ... ")

    ret = login(browser, username, passwd)
    if not ret:
        logging.error("login fail, abort.")
        return False

    time.sleep(3)

    # check login status
    loginRE = re.compile("https://tower.im/teams/\w+/projects/")
    if len(loginRE.findall(browser.current_url)) > 0:
        logging.debug("login successfully")
        print ("login successfully")
    else:
        logging.error("login successfully")
        print ("login error, url does not match.")
        return False

    # get team guid
    teamGuid = getLoginUserGuid(browser)

    teamMembersUrl = "https://tower.im/teams/%s/members/" % (teamGuid)
    browser.get(teamMembersUrl)
    time.sleep(2)
    browser.refresh()
    time.sleep(2)

    # get all member guids
    logging.debug("collecting all member guids ...")
    print ("collecting all member guids ...")
    memberGUIDs = getAllMemberGuids(browser)
    if len(memberGUIDs) == 0:
        logging.error("len of member guids is zero, finish.")
        return False

    # save members weekly screenshot
    logging.debug("saving weeklys screenshot ... ")
    print ("saving weeklys screenshot ...")
    weeklyStatistics = saveMembersWeeklyScreenshot(browser, memberGUIDs, membersPath)

    # save weekly report file
    reportFile = "HtmlReport.txt"
    reportFilePath = "%s/%s" % (savePath, reportFile)
    saveReportFile(reportFilePath, weeklyStatistics)

    # zip files
    logging.debug("zip screenshot files")
    print ("zipping files ...")
    #zipName = "%s/weeklys.zip" % (savePath)
    zipName = "%s/weeklys.tar.gz" % (savePath)
    ret = zipScreenshot(datePath, zipName)
    if not ret:
        logging.error("zip screenshot file fail.")
        return False

    # clean files
    logging.debug("clean screenshot files")
    print ("cleaning files ...")
    cleanPaths = []
    cleanPaths.append(datePath)
    cleanScreenshot(cleanPaths)

    return True


def login(browser, username, passwd):

    if browser.current_url == "https://tower.im/users/sign_in":
        unEL = browser.find_element_by_id("email")
        pwdEL = browser.find_element_by_name("password")
        unEL.send_keys(username)
        pwdEL.send_keys(passwd)
        unEL.submit()
        return True
    else:
        logging.error("Login error, it not a login url")
        return False

def getLoginUserGuid(browser):

    url = browser.current_url
    a = re.compile("https://tower.im/teams/(\w+)/\w+/")
    guids = a.findall(url)

    guid = ""
    if len (guids) > 0:
        guid = guids[0]

    return guid

def getAllMemberGuids(browser):

    memberGUIDs = []

    # default-group
    dfGroupELs = browser.find_elements_by_class_name("group-default")
    for g in dfGroupELs:
        memberELs = g.find_elements_by_class_name("member")
        for EL in memberELs:
            guid = EL.get_attribute("data-guid").strip()
            memberGUIDs.append(guid)

    # normal groups
    groupListEL = browser.find_element_by_class_name("grouplists")
    groupELs = groupListEL.find_elements_by_class_name("group")

    for g in groupELs:
        gnEL = g.find_element_by_class_name("group-name")
        gn = gnEL.text.strip()

        # filter the group
        if gn in GROUP_FILTER_LIST:
            continue

        memberELs = g.find_elements_by_class_name("member")
        for EL in memberELs:
            guid = EL.get_attribute("data-guid").strip()
            memberGUIDs.append(guid)

    return memberGUIDs


def saveMembersWeeklyScreenshot(browser, memberGUIDs, membersPath):

    weeklyStatistics = {}
    finish = []
    uncompleted = []
    noPermission = []

    for guid in memberGUIDs:
        url = "https://tower.im/members/%s/weekly_reports/" % guid
        browser.get(url)

        # filter users
        emailEL = browser.find_element_by_class_name("email")
        if emailEL.text.strip() in EMAIL_FILTER_LIST:
            continue
        name = browser.title.split("-")[0].strip()
        browser.save_screenshot("%s/%s.png" % (membersPath, name))

        nickName = browser.title.split("-")[0].strip()
        logging.debug(nickName)

        # count the statistic info
        if len(browser.find_elements_by_class_name("no-permission")) > 0:
            noPermission.append(nickName)
        elif len(browser.find_elements_by_class_name("uncompleted")) > 0:
            uncompleted.append(nickName)
        # count the login user's weekly
        elif len(browser.find_elements_by_class_name("btn-new-weekly-report")) > 0:
            uncompleted.append(nickName)
        else:
            finish.append(nickName)

    weeklyStatistics["NoPermission"] = noPermission
    weeklyStatistics["Uncompleted"] = uncompleted
    weeklyStatistics["Finish"] = finish

    return weeklyStatistics


def combineImages(savePath, subImagesDir, maxMember):
    """
    subImagesDir: the members' weeklys save path
    maxMember: max number of members in one output image
    """
    allImgObjs = []
    for imgName in os.listdir(subImagesDir):
        imgObj = Image.open(os.path.join(subImagesDir, imgName))

        # offset the header
        headerOffset = -80 # offset the image, cut the header
        imgObj = imgObj.offset(0, headerOffset)

        allImgObjs.append(imgObj)

    if len(allImgObjs) == 0:
        return False

    # offset the tail
    offsetH = 120

    oImgIndex = 0 # output image index

    container = []
    for i in range(len(allImgObjs)):

        container.append(allImgObjs[i])

        if (i + 1) % 20 and (i + 1) != len(allImgObjs):
            continue

        # get sum of height of container
        cmbImgHeight = 0
        for imgObj in container:
            cmbImgHeight += imgObj.size[1]

        oImgIndex = int(i / maxMember)

        # count the output image height
        cmbImgHeight -= offsetH * maxMember

        cmbImgWidth = container[0].size[0]
        cmbImgObj = Image.new("RGB", (cmbImgWidth, cmbImgHeight))
        lastHeight = 0
        for img in container:
            cmbImgObj.paste(img, (0, lastHeight))
            lastHeight += img.size[1]

            # offset
            lastHeight -= offsetH

        cmbImgObj.save("%s/weekly%s.png" % (savePath, oImgIndex))
        container.clear()

    return True


def work():

    logging.info("start weeklys screenshot work")
    print ("start ... ")

    if not DISPLAY:
        print ("hide display ... ")
        display = Display(visible=0, size=(1366, 768))
        display.start()

    config = getConfigObj()
    if config == None:
        return False
    userName = config.get("USER", "UserName")
    userPWD = config.get("USER", "userPWD")

    ret = getTowerWeeklyScreenshot(userName, userPWD, DEFAULT_SAVE_PATH)

    if not ret:
        print ('Error, abort. Please check the log file "%s"' % LOG_FILE)
        return False

    logging.info("finish all work, exit.")

    if not DISPLAY:
        display.stop()

    return True


_config = None
def getConfigObj():

    global _config
    if not _config:
        # check config file exist
        if not os.path.exists(CONFIG_FILE):
            print ("user configure file (TowerWeeklyRobot.ini) not found.")
            logging.error("user configure file (TowerWeeklyRobot.ini) not found.")
            return None
        _config = ConfigParser()
        _config.read(CONFIG_FILE)
    return _config


def zipScreenshot(zipDir, zipName):

    #cmd = "zip -r %s %s" %(zipName, zipDir)
    cmd = "tar -jcf %s %s" % (zipName, zipDir)

    logging.debug("zip screenshot ... ")
    logging.debug(cmd)

    ret = os.system(cmd)

    if ret == 0:
        return True
    return False


def cleanScreenshot(pathList):

    rmCmd = "rm -rf %s" % " ".join(pathList)

    logging.debug("clean screenshot...")
    logging.debug(rmCmd)

    os.system(rmCmd)


def saveReportFile(reportFilePath, weeklyStatistics):

    now = datetime.now()
    nowStr = str(now).split(".")[0]

    total = len(weeklyStatistics.get("Finish", [])) \
    + len(weeklyStatistics.get("Uncompleted", [])) \
    + len(weeklyStatistics.get("NoPermission", []))
    outputStr = """
    ------- Tower 周报机器人 ------- <br/>
    截图时间：%s <p>
    总人数: %d <p>
    完成周报人数: %d <br/>
      %s <p>
    没有周报记录: %d <br/>
      %s <p>
    没有查看权限: %d <br/>
      %s <p>
    """ % (nowStr,
            total,
            len(weeklyStatistics.get("Finish", [])),
            ", ".join(weeklyStatistics.get("Finish", [])),
            len(weeklyStatistics.get("Uncompleted", [])),
            ", ".join(weeklyStatistics.get("Uncompleted", [])),
            len(weeklyStatistics.get("NoPermission", [])),
            ", ".join(weeklyStatistics.get("NoPermission", []))
            )

    with open(reportFilePath, "w") as fp:
        fp.write(outputStr)

    return True


if __name__ == "__main__":
    work()

