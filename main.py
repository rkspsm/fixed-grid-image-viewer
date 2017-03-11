#! /usr/bin/env python3

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtMultimedia import *
from PyQt5.QtMultimediaWidgets import *
from math import *

from hashlib import sha256
import sys, os
import traceback

_args = sys.argv

class Stuff :

  width = 800
  height = 600
  scale_factor = 0.01
  next_k = {Qt.Key_D, Qt.Key_6, Qt.Key_Y}
  prev_k = {Qt.Key_A, Qt.Key_4, Qt.Key_E}
  refresh = {Qt.Key_X}
  pan_toggle = {Qt.Key_Z, Qt.Key_W, Qt.Key_2}
  remove_lines_button = {Qt.Key_C, Qt.Key_Home, Qt.Key_9}
  pick_line_color = {Qt.Key_Q}
  inc_play_rate = {Qt.Key_Up}
  dec_play_rate = {Qt.Key_Down}
  res_play_rate = {Qt.Key_F}
  seek_f = {Qt.Key_Right}
  seek_b = {Qt.Key_Left}
  seek_0 = {Qt.Key_R}
  play_pause = {Qt.Key_Space}

  overlays = ['grid.png']
  overlay_toggle = {Qt.Key_S, Qt.Key_5}

  seek_t = 2 # seconds
  zoom_button = Qt.MiddleButton
  pan_button = Qt.LeftButton
  pick_color_button = Qt.RightButton

  @staticmethod
  def isImage (f) :
    return f.endswith ('.jpg') or f.endswith ('.png') or f.endswith ('.jpeg')

  @staticmethod
  def isMovie (f) :
    return f.endswith ('.mkv') or f.endswith ('.avi') or f.endswith ('.mp4')

  @staticmethod
  def dist (p1, p2) :
    dx = p1[0] - p2[0]
    dy = p1[1] - p2[1]
    return sqrt (dx*dx + dy*dy)

  @staticmethod
  def tscale (t) :
    return (t.m11 (), t.m22 ())

  @staticmethod
  def string_of_rect (r) :
    return f'rect({r.x()}, {r.y()}, {r.width()}, {r.height()}'

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
      self.exit (1)

  def getFiles (self) :
    files = os.listdir (self.imgdir)
    files = [os.path.join (self.imgdir, x) for x in files]
    files = [x for x in files if os.path.isfile (x)]

    files = [x for x in files if Stuff.isImage (x) or Stuff.isMovie (x)]
    if len (files) == 0 :
      raise Exception ('no images in the dir')
    files = list (sorted (files))
    return files

  def setup (self) :
    self.isMedia = False
    self.playratepow = 0
    self.pan_on = True
    self.files = self.getFiles ()
    self.index = 0
    self.savedTransforms = dict ()

    self.lineColor = QColor (0, 0, 0)
    self.lines = []

    self.player = QMediaPlayer ()

    self.overlayItems = [self.scene.addPixmap (QPixmap (x)) for x in Stuff.overlays]
    for i, item in enumerate (self.overlayItems) :
      item.setZValue (10 + i)
      item.setVisible (False)

    try :
      skip = int (self.args[1])
    except :
      skip = 0

    self.filesOrIndexUpdated (True, skip)

    self.m_init ()
    self.k_init ()

  def removeLines (self) :
    for line in self.lines :
      self.scene.removeItem (line)
    self.lines = []

  def playrateUpdated (self) :
    pos = self.player.position ()
    self.player.setPlaybackRate (pow (2, self.playratepow))
    self.player.setPosition (pos)

  def getseekt (self) :
    factor = pow (2, self.playratepow)
    return Stuff.seek_t * factor * 1000

  def filesOrIndexUpdated (self, isFirst = False, skip = 0) :
    self.isMedia = False
    if not isFirst :
      self.player.stop ()
      skip = 0
      self.savedTransforms[self.lastDigest] = QTransform (self.imgItem.transform ())
      self.scene.removeItem (self.imgItem)
    self.index += skip
    self.index = 0 if self.index >= len (self.files) else self.index

    f = self.files[self.index]
    s = sha256 ()

    if Stuff.isImage (f) :
      with open (self.files[self.index], 'rb') as handle :
        s.update (handle.read ())
    else :
      s.update (f.encode ('utf-8'))
    d = s.digest ()

    if Stuff.isImage (f) :
      img = QPixmap (self.files[self.index])
      self.imgItem = self.scene.addPixmap (img)

      wrat = img.width () / Stuff.width
      hrat = img.height () / Stuff.height
    else :
      self.playratepow = 0
      self.mediaContent = QMediaContent (QUrl.fromLocalFile (f))
      self.player.setMedia (self.mediaContent)
      self.player.setMuted (True)
      self.imgItem = QGraphicsVideoItem ()
      self.player.setVideoOutput (self.imgItem)
      self.scene.addItem (self.imgItem)
      self.player.play ()
      self.isMedia = True

      wrat = 1
      hrat = 1
    rat = wrat if wrat > hrat else hrat

    if d in self.savedTransforms :
      self.curt = self.savedTransforms[d]
    else :
      self.curt = QTransform (self.imgItem.transform ()).scale (1 / rat, 1 / rat)
    self.imgItem.setTransform (self.curt)
    self.lastDigest = d
    self.removeLines ()

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
        self.linePt = self.gv.mapToScene (QPoint (e.x (), e.y ()))
      else :
        self.noscale = False

  def mr (self, e) :
    self.zoom_origin = None

    if e.button () == Stuff.pick_color_button :
      self.lineColor = QColorDialog.getColor ()

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
      if not self.pan_on :
        newPt = self.gv.mapToScene (QPoint (e.x (), e.y ()))
        line = self.scene.addLine (QLineF (self.linePt, newPt), QPen (self.lineColor, 2))
        line.setZValue (500)
        self.lines.append (line)
        self.linePt = newPt
        return
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

    elif e.key () in Stuff.pan_toggle :
      self.pan_on = not self.pan_on

    elif e.key () in Stuff.remove_lines_button :
      self.removeLines ()

    elif e.key () in Stuff.pick_line_color :
      self.lineColor = QColorDialog.getColor ()

    elif self.isMedia and e.key () in Stuff.inc_play_rate :
      self.playratepow += 1
      self.playrateUpdated ()

    elif self.isMedia and e.key () in Stuff.dec_play_rate :
      self.playratepow -= 1
      self.playrateUpdated ()

    elif self.isMedia and e.key () in Stuff.res_play_rate :
      self.playratepow = 0
      self.playrateUpdated ()

    elif self.isMedia and e.key () in Stuff.seek_f :
      t = self.getseekt ()
      pos = self.player.position ()
      pos += t
      pos = 0 if pos < 0 else pos
      self.player.setPosition (pos)

    elif self.isMedia and e.key () in Stuff.seek_b :
      t = self.getseekt ()
      pos = self.player.position ()
      pos -= t
      pos = 0 if pos < 0 else pos
      self.player.setPosition (pos)

    elif self.isMedia and e.key () in Stuff.seek_0 :
      self.player.setPosition (0)
      self.player.play ()

    elif self.isMedia and e.key () in Stuff.play_pause :
      state = self.player.state ()
      if state == QMediaPlayer.StoppedState :
        self.player.setPosition (0)
        self.player.play ()
      elif state == QMediaPlayer.PlayingState :
        self.player.pause ()
      elif state == QMediaPlayer.PausedState :
        self.player.play ()

  def go (self) :
    if self.err != '' :
      print (self.err)
      sys.exit (1)
    else :
      sys.exit (self.exec_ ())

App ().go ()

