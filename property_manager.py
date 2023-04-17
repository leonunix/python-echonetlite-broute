# coding: utf-8
from echonet_lite import Frame, Property
import datetime
import time
import subprocess
import struct
from logging import getLogger, StreamHandler, INFO, Formatter
logger = getLogger(__name__)


class PropertyManager:
    # キャッシュ対象のEPC
    cacheEPCs = (0x82, 0x8a, 0x8d, 0x9d, 0x9e, 0x9f, 0xe7, 0xe8)
    # サポートするEPC
    supportEPCs = [0x80, 0x81, 0x82, 0x88, 0x8a, 0x8d, 0x97, 0x98, 0x9d, 0x9e, 0x9f,
                   0xd3, 0xd7, 0xe0, 0xe1, 0xe2, 0xe3, 0xe4, 0xe5, 0xe7, 0xe8, 0xea, 0xeb, 0xec, 0xed]
    # 応答ESV
    resESVs = [0x72, 0x7a, 0x7e]
    # 通知ESV
    infESVs = [0x73, 0x74]

    def __init__(self):
        self._cache = {}
        self._requests = {}

    def setWisunManager(self, wisun):
        self._wisun = wisun
        if wisun is None:
            return
        wisun.setPropertyManager(self)

    def setEthernetManager(self, ether):
        self._ether = ether
        ether.setPropertyManager(self)

    # send frame to wisun
    def sendFrametoWisun(self, frame):
        logger.info("sendFrametoWisun: %s", frame)
        self._wisun.wisunSendFrame(frame)
        
    # send frame to ethernet
    def sendFrametoEthernet(self, frame):
        logger.info("sendFrametoEthernet: %s", frame)
        self._ether.sendResponse(frame)
        

