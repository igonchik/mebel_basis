# -*- coding: utf-8 -*-
# Симулятор раскроя
__author__ = "Dmitry Goncharov"
__version__ = "1.8.2"
__date__ = "2018-06-26"
__status__ = "beta"
__email__ = "igonchik@gmail.com"


import sys
from datetime import datetime
import os
import subprocess
from operator import itemgetter

from PyQt5 import QtCore
from PyQt5.QtGui import QColor
from PyQt5.QtGui import QPainter
from PyQt5.QtGui import QPen
from PyQt5.QtGui import QPixmap
from PyQt5.QtGui import QTransform
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QMainWindow
import main_ui


def inside_parenthesis(s):
    return s[s.find("(")+1:s.find(")")]


def try_to_int(s):
    try:
        return round(float(s.strip("\"")))
    except:
        return s


class RecordCut(object):
    __slots__ = "cut", "time_begin", "data", "name", "maxw", "maxh", "in_use", "zakaz", "gotovnost_list"


class AboutCut:
    def __init__(self):
        self.cuts = list()
        self.blocks = list()
        self.lines = list()


class BD:
    def __init__(self, bdname):
        self.BD = bdname
        self.input_stream = None

    def write(self, stream):
        self.input_stream = open(self.BD, "a")
        self.input_stream.write("{0}\n".format(stream))
        self.input_stream.close()


class Birka:
    def __init__(self, main):
        curp = os.path.join(os.path.dirname(__file__), 'config')
        filename = os.path.join(curp, "birka.ini")
        self.__ostatok = 1
        self.enum = 1300
        self.__bin_path = "C:\Program Files (x86)\BazisSoft\Simulator 10\Birka10.exe"
        self._homepath = os.path.expanduser('~')
        self.file_info = None
        self.__main = main
        with open(filename) as f:
            for l in f.readlines():
                l = "{0}".format(l)
                if l[-1] == '\n':
                    l = l[:-1]
                if l.startswith("ostatok="):
                    self.__ostatok = int(l[8:])
                elif l.startswith("bin_path="):
                    self.__bin_path = l[9:]
                elif l.startswith("bin_path="):
                    self.enum = l[8:]
                elif l.startswith("data_path="):
                    self._homepath = l[10:]

    def run(self, cut, repeat=True):
        if not self.file_info:
            self.file_info = QFileDialog.getOpenFileName(self.__main, 'Укажите файл с информацией о бирках',
                                                         self._homepath)[0]
        if not self.file_info:
            return
        count = int(cut[5]) if int(cut[5]) > 1 and repeat else 1
        try:
            subprocess.Popen([self.__bin_path, '/DATAFILE={0}'.format(self.file_info),
                              '/PRINT_RANGE={0},{1}:0,0'.format(str(cut[4]).strip(), count), '/PRINTER=',
                              '/NOMOVE_DATA', '/SILENT'])
        except:
            print("{0} {1} {2} {3} {4}".format('/DATAFILE={0}'.format(self.file_info),
                                                '/PRINT_RANGE={0},{1}:0,0'.format(str(cut[4]).strip(),
                                                                                  count),
                                                '/PRINTER=', '/NOMOVE_DATA', '/SILENT'))


class FileFormatReader:
    def __save__(self):
        r = RecordCut()
        r.cut = 0
        r.time_begin = datetime.now()
        r.data = self.__rec
        r.in_use = list()
        r.gotovnost_list = list()
        r.name = self.__name
        r.maxw = self.__maxw
        r.maxh = self.__maxh
        r.zakaz = self.__zakaz
        self.__rec = AboutCut()
        return r

    def get_maps(self):
        return self.__open_maps

    def __init__(self, filename):
        self.__rec = AboutCut()
        self.__container = list()
        self.__open_maps = list()
        self.__name = ''
        self.__zakaz = ''
        self.__maxw = 0
        self.__maxh = 0
        with open(filename) as f:
            for l in f.readlines():
                l = "{0}".format(l)
                if l.startswith("BOARDS,"):
                    finds = l.split(',')
                    self.__name = finds[3]
                    self.__maxw = try_to_int(finds[5])
                    self.__maxh = try_to_int(finds[6])
                    continue
                elif l[1:8] == "HEADER," or l.startswith("HEADER,") or l[1:].startswith("HEADER,"):
                    finds = l.split(',')
                    self.__zakaz = finds[2]
                    continue
                elif l.startswith("CUTS,"):
                    self.__container = self.__rec.cuts
                elif l.startswith("PATTERNS,"):
                    if len(self.__container) > 0:
                        self.__open_maps.append(self.__save__())
                        continue
                else:
                    continue
                inside = inside_parenthesis(l).split(',')
                try_to_int_list = list(map(try_to_int, inside))
                self.__container.append(try_to_int_list)

        if len(self.__container) > 0:
            self.__open_maps.append(self.__save__())


class Drawer:
    def draw_block(self, block, painter, color=None, pogr=[0, 0]):
        if color is None:
            color = QColor(145, 198, 98)
        painter.setBrush(color)
        painter.setPen(QPen(color, 0, QtCore.Qt.SolidLine))
        e = block
        painter.drawRect(e[0]-pogr[0], e[1]-pogr[1], e[2], e[3])

    @staticmethod
    def draw_line(line, painter, strong=False, color=None, pogr=[0, 0]):
        size = 30 if strong else 10
        line_type = QtCore.Qt.DotLine if strong else QtCore.Qt.SolidLine
        if color is None:
            color = QtCore.Qt.black
        painter.setPen(QPen(color, size, line_type))
        e = line
        painter.drawLine(e[0]-pogr[0], e[1]-pogr[1], e[2]-pogr[0], e[3]-pogr[1])

    @staticmethod
    def rect_from_coords(x1, y1, x2, y2):
        return [x1, y1, x2-x1, y2-y1]


class Main(QMainWindow, main_ui.Ui_MainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.setupUi(self)
        self.openButton.clicked.connect(self.open_file)
        self.prevButton.clicked.connect(self.prev_event)
        self.nextButton.clicked.connect(self.next_event)
        self.btn_mapl.clicked.connect(self.prev_map)
        self.btn_mapr.clicked.connect(self.next_map)
        self.recorder = BD("writer.log")
        self.data = None
        self.maps = list()
        self.current_map = 0
        self.current_cut = 0
        self.pic_size = [0, 0]
        self.drawer = Drawer()
        self.curp = os.path.join(os.path.dirname(__file__), 'icons')
        self.birka = Birka(self)
        self.par1_91_right = True
        self.in_use = list()
        self.shag = False
        self.next_enum = True

    def print_run(self, cut, repeat=True):
        self.birka.run(cut, repeat)

    def resizeEvent(self, event):
        if self.current_cut > 0 and len(self.maps) > 0:
            self.draw_cut()
        elif len(self.maps) > 0:
            self.draw_first()
        x = self.geometry().width()-129
        y1 = self.geometry().height() - 150
        y2 = self.geometry().height() - 280
        self.prevButton.setGeometry(x, y2, 120, 120)
        self.nextButton.setGeometry(x, y1, 120, 120)
        self.draw_backgrnd()
        QMainWindow.resizeEvent(self, event)

    def print_map(self):
        self.nextButton.setDisabled(True)
        self.prevButton.setDisabled(True)
        self.btn_mapl.setDisabled(True)
        self.btn_mapr.setDisabled(True)
        self.text_detal.setStyleSheet('')
        self.text_detal.setText('')
        self.data = self.maps[self.current_map-1].data
        if len(self.data.cuts[0]) >=7 and self.data.cuts[0][6] != self.maps[self.current_map-1].maxw:
            self.par1_91_right = False
        elif len(self.data.cuts[0]) < 7 and self.data.cuts[0][1] != self.maps[self.current_map-1].maxw:
            self.par1_91_right = False
        self.pic_size = [self.maps[self.current_map-1].maxw, self.maps[self.current_map-1].maxh]

        self.draw_first()
        self.current_cut = self.maps[self.current_map-1].cut
        for i in range(0, self.current_cut-1):
            self.about_cut(self.draw_cut(), False)
        self.text_plita.setText("  Плита: {0}x{1}".format(self.pic_size[0], self.pic_size[1]))
        self.statusbar.showMessage("Операция {0} из {1}".format(self.current_cut, len(self.data.cuts)))
        self.text_map.setText("  Карта: {1}/{0}".format(len(self.maps), self.current_map))

        if self.current_cut < (len(self.data.cuts) - 1):
            self.nextButton.setDisabled(False)
        if self.current_map < len(self.maps):
            self.btn_mapr.setDisabled(False)
        if self.current_map > 1:
            self.btn_mapl.setDisabled(False)
        if self.current_cut > 0:
            self.prevButton.setDisabled(False)

    def create_img(self):
        new_cuts = list()
        for i in range(1, len(self.data.cuts)):
            if self.data.cuts[i][5] < 90:
                new_cuts.append(self.data.cuts[i][4:10])
                if len(self.data.cuts[i]) > 10:
                    new_cuts[-1][-1] = -1
                for y in range(1, new_cuts[-1][5]):
                    new_cuts.append(self.data.cuts[i][4:10])
                    if len(self.data.cuts[i]) > 10:
                        new_cuts[-1][-1] = -1
        self.data.cuts = new_cuts

        new_lines = list()
        pb = 0
        #БЛОК x0 y0 ширина длина факт_детали номер_блока родительский_блок SEQ
        temp = [0, 0, self.maps[self.current_map-1].maxw, self.maps[self.current_map-1].maxh, 0, 1, pb, 0]
        new_blocks = [temp]
        new_blocks_ostatok = [[0, 0, self.maps[self.current_map-1].maxw, self.maps[self.current_map-1].maxh, new_cuts[0][1], pb]]
        block_id = 1
        last_shag = new_cuts[0][1]
        self.rip = list()

        for elem in new_cuts:
            gorizont = False
            if elem[1] % 2 == 1 and self.par1_91_right:
                gorizont = True
            if gorizont:
                if elem[1] <= last_shag:
                    for xx in range(len(new_blocks_ostatok)-1, -1, -1):
                        if new_blocks_ostatok[xx][4] == elem[1]:
                            temp = new_blocks_ostatok[xx]
                            pb = temp[5]
                            break
                else:
                    temp = new_blocks[-1]
                    pb = temp[5]
                if pb == 0:
                    pb = 1
                block_id += 1
                if pb == 1:
                    self.rip.append(block_id)
                new_blocks.append([temp[0], temp[1],
                                   temp[2], elem[2], elem[5], block_id, pb, elem[0]])
                new_blocks_ostatok.append([temp[0], temp[1]+elem[2],
                                           temp[2], temp[3]-elem[2], elem[1], pb])
                line = [temp[0], temp[1]+elem[2], temp[0]+temp[2], temp[1]+elem[2], elem[0]]
                last_shag = elem[1]
            else:
                if elem[1] <= last_shag:
                    for xx in range(len(new_blocks_ostatok)-1, -1, -1):
                        if new_blocks_ostatok[xx][4] == elem[1]:
                            temp = new_blocks_ostatok[xx]
                            pb = temp[5]
                            break
                else:
                    temp = new_blocks[-1]
                    pb = temp[5]
                if pb == 0:
                    pb = 1
                block_id += 1
                if pb == 1:
                    self.rip.append(block_id)
                new_blocks.append([temp[0], temp[1], elem[2],
                                   temp[3], elem[5],  block_id, pb, elem[0]])
                new_blocks_ostatok.append([temp[0]+elem[2], temp[1],
                                           temp[2]-elem[2], temp[3], elem[1], pb])
                line = [temp[0]+elem[2], temp[1], temp[0]+elem[2], temp[1]+temp[3], elem[0]]
                last_shag = elem[1]
            new_lines.append(line)

        sort_bk = list()
        for elem in new_blocks:
            sort_bk.append((elem[5], elem[6]))
        sort_bk = sorted(sort_bk, key=itemgetter(1))

        def app(sort_bk, cut, lm):
            lenk = 0
            for xl in sort_bk:
                if xl[6] == lm:
                    lenk += 1
                    cut.append(xl)
            len_cut = len(cut)
            for j in range(len_cut-1, len_cut-lenk-1, -1):
                app(sort_bk, cut, cut[j][5])
            if len(cut)+1 == len(sort_bk):
                return cut

        for rec in sort_bk:
            for xx in range(len(new_blocks)):
                if rec[0] == new_blocks[xx][5]:
                    self.data.blocks.append(new_blocks[xx])

        eee = app(self.data.blocks, list(), 1)
        self.data.cuts = list()
        self.data.blocks = [self.data.blocks[0]]
        temp_ee = list()
        for xx in eee:
            dk = xx[7]
            self.data.blocks.append(xx)
            for xl in new_lines:
                if dk == xl[4]:
                    self.data.lines.append(xl)
            for xl in new_cuts:
                if dk == xl[0] and dk not in temp_ee:
                    self.data.cuts.append(xl)
            temp_ee.append(dk)

    def open_file(self):
        filename = QFileDialog.getOpenFileName(self, 'Выберите файл раскроя', '.')[0]
        if filename:
            self.maps = FileFormatReader(filename).get_maps()
            self.text_zakaz.setText('Заказ: {0}'.format(self.maps[0].zakaz))
            self.text_material.setText('Материал: {0}'.format(self.maps[0].name))
        else:
            self.text_zakaz.setText('Заказ:')
            self.text_material.setText('Материал:')
        self.text_upor_l1.setText("0")
        self.text_upor_l2.setPixmap(QPixmap(os.path.join(self.curp, "align-horizontal-right.png")))
        self.text_upor_r.setText("0")
        self.current_map = 1
        if len(self.maps) == 0:
            return
        self.print_map()

    def next_map(self):
        if self.current_map == len(self.maps):
            return
        self.current_map += 1
        if self.current_map == len(self.maps):
            self.btn_mapr.setDisabled(True)
        if self.current_map > 1:
            self.btn_mapl.setDisabled(False)
        self.print_map()

    def prev_map(self):
        if self.current_map == 0:
            return
        self.current_map -= 1
        if self.current_map == 1:
            self.btn_mapl.setDisabled(True)
        if self.current_map < len(self.maps):
            self.btn_mapr.setDisabled(False)
        self.print_map()

    def prev_event(self):
        if self.data is None:
            return
        if self.current_cut == 1:
            return self.prev_map()
        self.current_cut -= 1
        self.shag = False
        self.next_enum = False

        cut = self.data.cuts[self.current_cut-1]
        if cut[3] > 1:
            last_pravo = None
            for blk in self.data.blocks:
                if blk[7] == self.data.blocks[self.current_cut][7]:
                    block = blk
                    pravo = False
                    blkm = False
                    for blk1 in self.data.blocks:
                        if blk1[5] == block[6]:
                            blkm = block[2] <= (blk1[2] - block[2] - block[0])
                            break
                    if cut[2] <= self.birka.enum and cut[5] == -1 and cut[1] % 2 == 1:
                        pravo = True
                    if block[3] / block[2] >= 4 and cut[1] % 2 == 1 and cut[5] >= 0:
                        pravo = True
                    if block[2] <= self.birka.enum and cut[1] % 2 != 1 and cut[5] >= 0 and blkm:
                        pravo = True
                    if last_pravo is not None:
                        last_pravo = last_pravo == pravo
                    else:
                        last_pravo = pravo
            if last_pravo:
                self.current_cut = self.current_cut - cut[3] + 1
                self.shag = True

        #if self.current_cut == 1:
        #    self.prevButton.setDisabled(True)
        if self.current_map == 1 and self.current_cut == 1:
            self.prevButton.setDisabled(True)
        if self.current_cut <= len(self.data.cuts):
            self.nextButton.setDisabled(False)
        self.statusbar.showMessage("Операция {0} из {1}".format(self.current_cut, len(self.data.cuts)))
        self.maps[self.current_map-1].cut = self.current_cut
        self.about_cut(self.draw_cut())

    def next_event(self):
        if self.data is None:
            return
        if self.current_cut == len(self.data.cuts):
            return self.next_map()
        self.current_cut += 1
        self.next_enum = True

        cut = self.data.cuts[self.current_cut-1]
        self.shag = False
        if cut[3] > 1:
            last_pravo = None
            for blk in self.data.blocks:
                if blk[7] == self.data.blocks[self.current_cut][7]:
                    block = blk
                    pravo = False
                    blkm = False
                    for blk1 in self.data.blocks:
                        if blk1[5] == block[6]:
                            blkm = block[2] <= (blk1[2] - block[2] - block[0])
                            break
                    if cut[2] <= self.birka.enum and cut[5] == -1 and cut[1] % 2 == 1:
                        pravo = True
                    if block[3] / block[2] >= 4 and cut[1] % 2 == 1 and cut[5] >= 0:
                        pravo = True
                    if block[2] <= self.birka.enum and cut[1] % 2 != 1 and cut[5] >= 0 and blkm:
                        pravo = True
                    if last_pravo is not None:
                        last_pravo = (last_pravo == pravo)
                    else:
                        last_pravo = pravo
            if last_pravo:
                self.current_cut = self.current_cut + cut[3] - 1
                self.shag = True

#        if self.current_cut == len(self.data.cuts):
#            self.nextButton.setDisabled(True)

        if self.current_map == len(self.maps) and self.current_cut == len(self.data.cuts):
            self.nextButton.setDisabled(True)

        if self.current_cut > 1:
            self.prevButton.setDisabled(False)
        self.maps[self.current_map-1].cut = self.current_cut
        self.statusbar.showMessage("Операция {0} из {1}".format(self.current_cut, len(self.data.cuts)))

        self.recorder.write("{0};{1};{2};{3}"
                            .format(datetime.now().strftime('%Y-%m-%d'),
                                    self.maps[self.current_map-1].time_begin.strftime('%H:%M:%S'),
                                    datetime.now().strftime('%H:%M:%S'),
                                    self.current_map))

        self.maps[self.current_map-1].time_begin = datetime.now()
        self.about_cut(self.draw_cut())

    def about_cut(self, cut, birka=True):
        # Вывод информации о разрезе
        self.maps[self.current_map-1].gotovnost_list = list()
        for rec in range(self.current_cut+1):
            if self.data.blocks[rec][4] >= 1:
                self.maps[self.current_map-1].gotovnost_list.append(self.data.blocks[rec][5])

        if cut[5] == -1:
            e7 = "Полоса"
            self.text_detal.setStyleSheet('background-color: green')
        elif cut[5] >= 1:
            e7 = "Готовая деталь"
            self.text_detal.setStyleSheet('background-color: red')
            if birka and self.next_enum:
                self.print_run(cut, repeat=self.shag)
        elif cut[5] == 0:
            e7 = "Незаконченная деталь"
            self.text_detal.setStyleSheet('background-color: yellow')
        else:
            e7 = "Полезный отход"
            if birka:
                self.print_run(cut, repeat=self.shag)
            self.text_detal.setStyleSheet('background-color: gray')
        block = self.data.blocks[self.current_cut]
        block8 = "{0} ({1}x{2})".format(e7, block[2], block[3])
        self.text_detal.setText(block8)
        block9 = ""
        if self.shag and int(cut[3]) > 1:
            block9 = "{0}x".format(cut[3])
        self.text_detal_alarm.setText(block9)
        self.text_upor_l1.setDisabled(True)
        self.text_upor_r.setDisabled(True)
        self.text_upor_l1t.setDisabled(True)
        self.text_upor_rt.setDisabled(True)

        pravo = False
        blkm = False
        for blk in self.data.blocks:
            if blk[5] == block[6]:
                blkm = block[2] <= (blk[2] - block[2] - block[0])
                break

        if cut[2] <= self.birka.enum and cut[5] == -1 and cut[1] % 2 == 1:
            pravo = True
        if block[3] / block[2] >= 4 and cut[1] % 2 == 1 and cut[5] >= 0:
            pravo = True
        if block[2] <= self.birka.enum and cut[1] % 2 != 1 and cut[5] >= 0 and blkm:
            pravo = True

        if pravo or (cut[1] % 2 == 1 and self.par1_91_right):
            self.text_upor_l1.setText("0")
            self.text_upor_r.setText(str(cut[2]))
            self.text_upor_r.setDisabled(False)
            self.text_upor_rt.setDisabled(False)
            self.text_upor_r.setStyleSheet('background-color: white')
            self.text_upor_l1.setDisabled(True)
            self.text_upor_l1t.setDisabled(True)
            self.text_upor_l1.setStyleSheet('')
        else:
            self.text_upor_l1.setText(str(cut[2]))
            self.text_upor_r.setText("0")
            self.text_upor_l1.setDisabled(False)
            self.text_upor_l1t.setDisabled(False)
            self.text_upor_r.setDisabled(True)
            self.text_upor_rt.setDisabled(True)
            self.text_upor_r.setStyleSheet('')
            self.text_upor_l1.setStyleSheet('background-color: white')

    def draw_cut(self):
        # Прорисовка разреза
        cuts = self.data.cuts
        lines = self.data.lines
        painter = QPainter()
        cut = cuts[self.current_cut-1]
        block = self.data.blocks[0]
        tblock = self.data.blocks[self.current_cut]
        for elem in self.data.blocks:
            if elem[5] == tblock[6]:
                block = elem
                break

        pravo = False
        blkm = False
        for block in self.data.blocks:
            if block[5] == tblock[6]:
                blkm = tblock[2] <= (block[2] - tblock[2] - tblock[0])
                break
        if cut[2] <= self.birka.enum and cut[5] == -1 and cut[1] % 2 == 1:
            pravo = True
        if tblock[3] / tblock[2] >= 4 and cut[1] % 2 == 1 and cut[5] >= 0:
            pravo = True
        if tblock[2] <= self.birka.enum and cut[1] % 2 != 1 and cut[5] >= 0 and blkm:
            pravo = True

        self.in_use = list()
        for elem in self.data.blocks:
            if elem[7] > tblock[7] and elem[6] == tblock[6]:
                self.in_use.append(elem)
            if elem[7] == tblock[7] and elem[6] == tblock[6] and elem[5] < tblock[5] and not self.shag:
                self.in_use.append(elem)
        strong_lines = [line for line in lines if line[4] == cut[0]]

        # Прорисовка блока на нижней схеме
        pixmap = QPixmap(block[2], block[3])
        pixmap.fill(QtCore.Qt.white)
        painter.begin(pixmap)
        color = QColor(150, 255, 150)

        transform_deg = 0
        last_x = 0
        last_y = 0
        by_x = 0
        by_y = 0
        for elem in strong_lines:
            if elem[0] == elem[2] and last_x < elem[0]:
                last_x = elem[2]
            if elem[1] == elem[3] and last_y < elem[1]:
                last_y = elem[3]
        self.text_upor_l2.setPixmap(QPixmap(os.path.join(self.curp, "align-horizontal-right.png")))
        for elem in strong_lines:
            if elem[1] == elem[3] and last_y == elem[1]:
                if (block[1] + block[3] // 2) > elem[1]:
                    transform_deg = 90
                    self.text_upor_l2.setPixmap(QPixmap(os.path.join(self.curp, "align-vertical-top.png")))
                else:
                    transform_deg = 90
                    self.text_upor_l2.setPixmap(QPixmap(os.path.join(self.curp, "align-vertical-top.png")))
            elif elem[0] == elem[2] and pravo:
                transform_deg = 180
                by_x = -by_x

        for elem in self.in_use:
            if elem[2] == block[2]:
                by_y += elem[3] // 2
            if elem[3] == block[3]:
                by_x += elem[2] // 2
        self.drawer.draw_block(block, painter, color, [block[0]+by_x, block[1]+by_y])
        for elem in self.in_use:
            self.drawer.draw_block(elem, painter, QtCore.Qt.white, [block[0]+by_x, block[1]+by_y])
        for elem in strong_lines:
            self.drawer.draw_line(elem, painter, True, pogr=[block[0]+by_x, block[1]+by_y])

        painter.end()
        trasform = QTransform()
        trasform.rotate(transform_deg)
        pixmap = pixmap.transformed(trasform)
        self.picture2.setPixmap(pixmap.scaled(self.picture2.size().width()*0.8, self.picture2.size().height()*0.8, QtCore.Qt.KeepAspectRatio))

        # Уже обработанные блоки
        pixmap = QPixmap(*self.pic_size)
        pixmap.fill(QtCore.Qt.white)
        painter = QPainter()
        painter.begin(pixmap)
        for elem in self.data.blocks:
            if elem[7] < block[7]:
                self.drawer.draw_block(elem, painter, QtCore.Qt.gray)

        # Активный блок
        self.drawer.draw_block(block, painter, QtCore.Qt.red)
        for elem in self.data.blocks:
            if elem[5] in self.maps[self.current_map-1].gotovnost_list:
                self.drawer.draw_block(elem, painter, QtCore.Qt.yellow)
        for elem in self.data.lines:
            self.drawer.draw_line(elem, painter)
        painter.end()
        self.picture.setPixmap(pixmap.scaled(self.picture.size(), QtCore.Qt.KeepAspectRatio))
        return cut

    def draw_backgrnd(self):
        # Прорисовка белого фона для схем и привязка его к координатам
        x = 9
        y = self.verticalLayout_2.itemAt(0).geometry().height() + 19
        wh = self.verticalLayout_2.itemAt(0).geometry().width()
        ht1 = self.verticalLayout_2.itemAt(1).geometry().height()
        pixmap = QPixmap(wh, ht1)
        pixmap.fill(QtCore.Qt.white)
        self.fone.setGeometry(x, y, wh, ht1)
        self.fone.setPixmap(pixmap.scaled(self.fone.size(), QtCore.Qt.KeepAspectRatio))
        y = y + ht1 + 9
        self.fone1.setGeometry(x, y, wh, ht1)
        self.fone1.setPixmap(pixmap.scaled(self.fone1.size(), QtCore.Qt.KeepAspectRatio))

    def draw_first(self):
        if len(self.data.lines) == 0:
            self.create_img()
        # Прорисовка файла раскроя при открытии
        main_pixmap = QPixmap(*self.pic_size)
        main_pixmap.fill(QtCore.Qt.white)
        self.picture2.setPixmap(main_pixmap.scaled(self.picture.size(), QtCore.Qt.KeepAspectRatio))
        painter = QPainter()
        painter.begin(main_pixmap)
        self.draw_all(painter)
        painter.end()
        self.picture.setPixmap(main_pixmap.scaled(self.picture.size(), QtCore.Qt.KeepAspectRatio))
        self.draw_backgrnd()

    def draw_all(self, painter):
        # Прорисовка всех элементов раскроя
        for elem in self.data.blocks:
            self.drawer.draw_block(elem, painter, QtCore.Qt.gray)
        for elem in self.data.lines:
            self.drawer.draw_line(elem, painter)


app = QApplication(sys.argv)
dialog = Main()
dialog.show()
app.exec()
