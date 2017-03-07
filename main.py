#! /usr/bin/env python3

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from math import *

import sys, os
import traceback

_args = sys.argv

class Stuff :

  width = 800
  height = 600
  scale_factor = 0.01
  next_k = {Qt.Key_D}
  prev_k = {Qt.Key_A}
  refresh = {Qt.Key_Y}

  overlays = ['grid.png']
  overlay_toggle = {Qt.Key_S}

  zoom_button = Qt.MiddleButton
  pan_button = Qt.LeftButton

  @staticmethod
  def dist (p1, p2) :
    dx = p1[0] - p2[0]
    dy = p1[1] - p2[1]
    return sqrt (dx*dx + dy*dy)

  @staticmethod
  def tscale (t) :
    return (t.m11 (), t.m22 ())

class GfxView (QGraphicsView) :
  def setMHandlers (self, mp, mm, mr) :
    self.mp = mp
    self.mm = mm
    self.mr = mr

  def setKHandlers (self, kp, kr) :
    self.kp = kp
    self.kr = kr

  def mousePressEvent (self, e) :
    self.mp (e)

  def mouseReleaseEvent (self, e) :
    self.mr (e)

  def mouseMoveEvent (self, e) :
    self.mm (e)

  def keyPressEvent (self, e) :
    self.kp (e)

  def keyReleaseEvent (self, e) :
    self.kr (e)

  def sizeHint (self) :
    return QSize (Stuff.width, Stuff.height)

class App (QApplication) :
  def __init__ (self) :
    QApplication.__init__ (self, _args)

    self.args = _args[1:]

    self.scene = QGraphicsScene ()
    self.scene.setSceneRect (0, 0, Stuff.width, Stuff.height)
    self.gv = GfxView (self.scene)
    self.gv.setHorizontalScrollBarPolicy (Qt.ScrollBarAlwaysOff)
    self.gv.setVerticalScrollBarPolicy (Qt.ScrollBarAlwaysOff)
    self.gv.show ()

    self.err = ''
    try :
      self.imgdir = self.args[0]
      assert (os.path.isdir (self.imgdir))
      self.setup ()
    except :
      traceback.print_exc ()
      self.err = 'usage: <prog> <imgdir>'

  def getFiles (self) :
    files = os.listdir (self.imgdir)
    files = [os.path.join (self.imgdir, x) for x in files]
    files = [x for x in files if os.path.isfile (x)]
    isImage = lambda f : (
      f.endswith ('.jpg') or
      f.endswith ('.png') or
      f.endswith ('.jpeg')
    )

    files = [x for x in files if isImage (x)]
    files = list (sorted (files))
    return files

  def setup (self) :
    self.files = self.getFiles ()
    self.index = 0

    self.overlayItems = [self.scene.addPixmap (QPixmap (x)) for x in Stuff.overlays]
    for i, item in enumerate (self.overlayItems) :
      item.setZValue (1 + i)

    self.filesOrIndexUpdated (True)

    self.m_init ()
    self.k_init ()

  def filesOrIndexUpdated (self, isFirst = False) :
    if not isFirst :
      self.scene.removeItem (self.imgItem)
    img = QPixmap (self.files[self.index])
    self.imgItem = self.scene.addPixmap (img)

    wrat = img.width () / Stuff.width
    hrat = img.height () / Stuff.height
    rat = wrat if wrat > hrat else hrat

    self.curt = QTransform (self.imgItem.transform ()).scale (1 / rat, 1 / rat)
    self.imgItem.setTransform (self.curt)

  def m_init (self) :
    self.gv.setMHandlers (self.mp, self.mm, self.mr)
    self.zoom_origin = None
    self.noscale = True
    pass

  def mp (self, e) :
    if e.button () == Stuff.zoom_button or e.button () == Stuff.pan_button :
      self.zoom_origin = (e.x (), e.y ())

      self.curt = QTransform (self.imgItem.transform ())

      if e.button () == Stuff.pan_button :
        self.noscale = True
      else :
        self.noscale = False

  def mr (self, e) :
    self.zoom_origin = None

  def zoi (self) :
    pt = QPoint (self.zoom_origin[0], self.zoom_origin[1])
    pts = self.gv.mapToScene (pt)
    pti = self.imgItem.mapFromScene (pts)

    return pti

  def mm (self, e) :
    if self.zoom_origin is None :
      return

    pt = (e.x (), e.y ())
    #d = Stuff.dist (pt, self.zoom_origin)
    dx = pt[0] - self.zoom_origin[0]
    dy = pt[1] - self.zoom_origin[1]
    if self.noscale :
      scale = self.curt.m11 ()
      self.tempt = QTransform (self.curt).translate (dx / scale, dy / scale)
      self.imgItem.setTransform (self.tempt)
    else :
      scale = 1 + dx * Stuff.scale_factor
      #self.tempt = QTransform (self.curt).scale (scale, scale)
      z1 = self.zoi ()
      self.tempt = QTransform (self.curt).translate (- self.curt.dx (), - self.curt.dy ()).scale (scale, scale).translate (self.curt.dx (), self.curt.dy ())
      self.imgItem.setTransform (self.tempt)
      z2 = self.zoi ()
      dx = z2.x () - z1.x ()
      dy = z2.y () - z1.y ()
      self.tempt.translate (dx, dy)
      self.imgItem.setTransform (self.tempt)

  def k_init (self) :
    self.gv.setKHandlers (self.kp, self.kr)

  def kp (self, e) :
    pass

  def kr (self, e) :
    if e.key () in Stuff.next_k :
      self.index += 1
      self.filesOrIndexUpdated ()
    elif e.key () in Stuff.prev_k :
      self.index -= 1
      self.filesOrIndexUpdated ()
    elif e.key () in Stuff.overlay_toggle :
      for item in self.overlayItems :
        item.setVisible (not item.isVisible ())
    elif e.key () in Stuff.refresh :
      newFiles = self.getFiles ()
      curFile = self.files[self.index]
      if curFile in newFiles :
        newIndex = newFiles.index (curFile)
      else :
        newIndex = self.index

      self.files = newFiles
      self.index = newIndex

  def go (self) :
    if self.err != '' :
      print (self.err)
      sys.exit (1)
    else :
      sys.exit (self.exec_ ())

App ().go ()

