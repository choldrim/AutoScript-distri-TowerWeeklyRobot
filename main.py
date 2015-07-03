#!/usr/bin/env python3
# encoding: utf-8

import time
import os
import logging

from configparser import ConfigParser
from datetime import datetime

from pyvirtualdisplay import Display
from selenium import webdriver
from PIL import Image

DISPLAY = False
DEFAULT_SAVE_PATH = "weeklys"
MAX_MEMBER_IN_ONE_IMAGE = 20
GROUP_FILTER_LIST=["总经办", "CrossOver 援兵", "江南援兵", "合作伙伴"]
LOG_FILE = "WeeklyRobot.log"

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
    ret = login(browser, username, passwd)
    if not ret:
        logging.error("login fail, abort.")
        return False

    logging.debug("login successfully")

    time.sleep(2)

    teamUrl = "https://tower.im/teams/0/members/"
    browser.get(teamUrl)
    time.sleep(1)
    browser.refresh()

    # get all member guids
    logging.debug("get all member guids")
    memberGUIDs = getAllMemberGuids(browser)
    if len(memberGUIDs) == 0:
        logging.error("len of member guids is zero, finish.")
        return False

    # save members weekly screenshot
    logging.debug("save weeklys screenshot")
    saveMembersWeeklyScreenshot(browser, memberGUIDs, membersPath)

    # combine
    logging.debug("combine weeklys screenshot")
    ret = combineImages(datePath, membersPath, MAX_MEMBER_IN_ONE_IMAGE)
    if not ret:
        logging.error("combine weeklys screenshot fail.")
        return False

    # zip files
    logging.debug("zip screenshot file")
    #zipName = "%s/%s.zip" % (savePath, dateStr)
    zipName = "%s/weeklys.zip" % (savePath)
    ret = zipScreenshot(datePath, zipName)
    if not ret:
        logging.error("zip screenshot file fail.")
        return False

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
        logging.error("it not login url")
        return False


def getAllMemberGuids(browser):

    memberGUIDs = []

    # default-group
    dfGroupELs = browser.find_elements_by_class_name("group-default")
    for g in dfGroupELs:
        memberELs = g.find_elements_by_class_name("member")
        for EL in memberELs:
            guid = EL.get_attribute("data-guid")
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
            guid = EL.get_attribute("data-guid")
            memberGUIDs.append(guid)

    return memberGUIDs


def saveMembersWeeklyScreenshot(browser, memberGUIDs, membersPath):
    for guid in memberGUIDs:
        url = "https://tower.im/members/%s/weekly_reports/" % guid
        browser.get(url)
        name = browser.title.split("-")[0]
        browser.save_screenshot("%s/%s.png" % (membersPath, name))

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

    if not DISPLAY:
        display = Display(visible=0, size=(1366, 768))
        display.start()

    config = getConfigObj()
    userName = config.get("USER", "UserName")
    userPWD = config.get("USER", "userPWD")
    ret = getTowerWeeklyScreenshot(userName, userPWD, DEFAULT_SAVE_PATH)

    if ret:
        pass

    logging.info("finish all work, exist.")

    if not DISPLAY:
        display.stop()


def getConfigObj():

    config = ConfigParser()
    config.read("main.ini")
    return config


def zipScreenshot(zipDir, zipName):

    cmd = "zip -r %s %s" %(zipName, zipDir)
    logging.debug("zip screenshot: %s " % cmd)
    ret = os.system(cmd)

    if ret == 0:
        return True
    return False


if __name__ == "__main__":
    work()

