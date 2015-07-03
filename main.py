#!/usr/bin/env python3
# encoding: utf-8

import time
import os

from pyvirtualdisplay import Display
from selenium import webdriver
#from selenium.webdriver.remote.errorhandler import NoSuchElementException
from PIL import Image


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
    dateStr = "2015-06-26"
    datePath = "%s/%s" % (savePath, dateStr)
    membersPath = "%s/members" %(datePath)
    os.makedirs(membersPath, exist_ok=True)

    # login
    ret = login(browser, username, passwd)
    if not ret:
        return False

    time.sleep(2)

    teamUrl = "https://tower.im/teams/0/members/"
    browser.get(teamUrl)
    #browser.reflash()

    # get all member guids
    memberGUIDs = getAllMemberGuids(browser)

    # save members weekly screenshot
    saveMembersWeeklySS(browser, memberGUIDs, membersPath)

    # combine
    ret = combineImages(datePath, membersPath)

    return ret


def login(browser, username, passwd):
    # login
    if browser.current_url == "https://tower.im/users/sign_in":
        unEL = browser.find_element_by_id("email")
        pwdEL = browser.find_element_by_name("password")
        unEL.send_keys(username)
        pwdEL.send_keys(passwd)
        unEL.submit()
        return True
    else:
        print ("there may be some error, it is not a login url:%s" % browser.current_url)
        return False

def getAllMemberGuids(browser):
    memberGUIDs = []
    memberELs = browser.find_elements_by_class_name("member")
    for EL in memberELs:
        guid = EL.get_attribute("data-guid")
        memberGUIDs.append(guid)
        print (guid)
    return memberGUIDs

def saveMembersWeeklySS(browser, memberGUIDs, membersPath):
    for guid in memberGUIDs:
        url = "https://tower.im/members/%s/weekly_reports/" % guid
        browser.get(url)
        name = browser.title.split("-")[0]
        browser.save_screenshot("%s/%s.png" % (membersPath, name))

def combineImages(savePath, subImagesDir):
    imgObjs = []
    cmbImgHeight = 0
    for imgName in os.listdir(subImagesDir):
        imgObj = Image.open(os.path.join(subImagesDir, imgName))

        # offset the header
        imgObj = imgObj.offset(0, -80)

        imgObjs.append(imgObj)
        cmbImgHeight += imgObj.size[1]

        if len(imgObjs) > 20:
            break

    if len(imgObjs) == 0:
        return False

    # offset
    offsetH = 120
    cmbImgHeight -= offsetH * len(imgObjs)

    cmbImgWidth = imgObjs[0].size[0]
    cmbImgObj = Image.new("RGB", (cmbImgWidth, cmbImgHeight))
    lastHeight = 0
    for img in imgObjs:
        cmbImgObj.paste(img, (0, lastHeight))
        lastHeight += img.size[1]

        # offset
        lastHeight -= offsetH

    cmbImgObj.save("%s/weekly.png" % savePath)

    return True

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print ("args are not enough")
        quit()

    #saveWebScreenshot(sys.argv[1], sys.argv[2])
    #ret = getTowerWeeklyScreenshot(sys.argv[1], sys.argv[2], sys.argv[3])
    ret = combineImages("weeklys", "weeklys/2015-06-26/members")

    if ret:
        print ("finish.")
    else:
        print ("error.")
