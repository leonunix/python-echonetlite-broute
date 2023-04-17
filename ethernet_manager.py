# coding: utf-8
import time
from echonet_lite import Object, Frame, Node, Property
import echonet_lite
from threading import Event, Thread
from logging import getLogger, StreamHandler, INFO, Formatter
logger = getLogger(__name__)
logger.setLevel(INFO)


class EthernetManager(Object):
    ''' SmartMeter Object (group=0x02, class=0x88) '''
    # リクエストID
    # requestId = 0

    def __init__(self):
        Object.__init__(self, 0x02, 0x88)
        self._recAddr = {}
        self._propMan = None
        self._Thread = None
        self._node = None
        self.addr = ""

    # Propertyマネージャ設定
    def setPropertyManager(self, pm):
        self._propMan = pm

    # Ethernet処理タスク開始
    def start(self):
        self._stopReceiveEvent = False
        self._Thread = Thread(target=self._task)
        self._Thread.start()

    # Ethernet処理タスク終了
    def stop(self):
        if self._Thread is None:
            return
        self._stopReceiveEvent = True
        self._Thread.join()

    # Ethernet処理タスク        
    def _task(self):
        logger.info('receive task start')
        # EthernetベースのEchonet開始
        self._node = Node()
        self._node.add_object(self)
        while not self._stopReceiveEvent:
            self._node.recvfrom()
        # node.loop()
        logger.info('receive task end')

    # Echonet受信
    def service(self, frame, addr):
        #logger.info(frame)
        self._propMan.sendFrametoWisun(frame)
        self.addr = addr[0]
        return None

    # Echonet送信（応答）
    def sendResponse(self, frame, ):
        if self._node is not None:
            self._node.sendto(frame.get_bytes(), self.addr)

    # Echonet送信（通知）
    def sendNotification(self, frame):
        if self._node is not None:
            self._node.sendto(frame.get_bytes(), '224.0.23.0')


if __name__ == '__main__':
    try:
        logger.info('EthernetManager start')
        em = EthernetManager()
        node = Node()
        node.add_object(em)
        node.loop()
    except KeyboardInterrupt:
        pass
