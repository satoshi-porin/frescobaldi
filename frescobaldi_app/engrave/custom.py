# This file is part of the Frescobaldi project, http://www.frescobaldi.org/
#
# Copyright (c) 2008 - 2014 by Wilbert Berendsen
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
# See http://www.gnu.org/licenses/ for more information.

"""
Custom engraving dialog.
"""

from __future__ import unicode_literals

import os
import collections

from PyQt4.QtCore import QSettings, QSize
from PyQt4.QtGui import (QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QGridLayout, QLabel, QTextEdit)

import app
import documentinfo
import userguide
import icons
import job
import jobmanager
import panelmanager
import lilypondinfo
import listmodel
import widgets
import qutil
import util

from . import command


class Dialog(QDialog):
    def __init__(self, mainwindow):
        super(Dialog, self).__init__(mainwindow)
        self._document = None
        
        layout = QGridLayout()
        self.setLayout(layout)
        
        self.versionLabel = QLabel()
        self.versionCombo = QComboBox()
        
        self.outputLabel = QLabel()
        self.outputCombo = QComboBox()
        
        self.resolutionLabel = QLabel()
        self.resolutionCombo = QComboBox(editable=True)
        
        self.modeLabel = QLabel()
        self.modeCombo = QComboBox()
        
        self.englishCheck = QCheckBox()
        self.deleteCheck = QCheckBox()
        
        self.commandLineLabel = QLabel()
        self.commandLine = QTextEdit(acceptRichText=False)
        
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Ok).setIcon(icons.get("lilypond-run"))
        userguide.addButton(self.buttons, "engrave_custom")
        
        self.resolutionCombo.addItems(['100', '200', '300', '600', '1200'])
        self.resolutionCombo.setCurrentIndex(2)
        
        self.modeCombo.addItems(['preview', 'publish', 'debug'])
        layout.addWidget(self.versionLabel, 0, 0)
        layout.addWidget(self.versionCombo, 0, 1)
        layout.addWidget(self.outputLabel, 1, 0)
        layout.addWidget(self.outputCombo, 1, 1)
        layout.addWidget(self.resolutionLabel, 2, 0)
        layout.addWidget(self.resolutionCombo, 2, 1)
        layout.addWidget(self.modeLabel, 3, 0)
        layout.addWidget(self.modeCombo, 3, 1)
        layout.addWidget(self.englishCheck, 4, 0, 1, 2)
        layout.addWidget(self.deleteCheck, 5, 0, 1, 2)
        layout.addWidget(self.commandLineLabel, 6, 0, 1, 2)
        layout.addWidget(self.commandLine, 7, 0, 1, 2)
        layout.addWidget(widgets.Separator(), 8, 0, 1, 2)
        layout.addWidget(self.buttons, 9, 0, 1, 2)
        
        app.translateUI(self)
        qutil.saveDialogSize(self, "engrave/custom/dialog/size", QSize(480, 260))
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        
        model = listmodel.ListModel(formats, display=lambda f: f.title(),
            icon=lambda f: icons.file_type(f.type))
        self.outputCombo.setModel(model)
        
        s = QSettings()
        s.beginGroup("lilypond_settings")
        self.englishCheck.setChecked(
            s.value("no_translation", False, bool))
        self.deleteCheck.setChecked(
            s.value("delete_intermediate_files", True, bool))
        
        if s.value("default_output_target", "pdf", type("")) == "svg":
            self.outputCombo.setCurrentIndex(3)
        
        self.loadLilyPondVersions()
        self.selectLilyPondInfo(lilypondinfo.preferred())
        app.settingsChanged.connect(self.loadLilyPondVersions)
        app.jobFinished.connect(self.slotJobFinished)
        self.outputCombo.currentIndexChanged.connect(self.makeCommandLine)
        self.modeCombo.currentIndexChanged.connect(self.makeCommandLine)
        self.deleteCheck.toggled.connect(self.makeCommandLine)
        self.resolutionCombo.editTextChanged.connect(self.makeCommandLine)
        self.makeCommandLine()
        panelmanager.manager(mainwindow).layoutcontrol.widget().optionsChanged.connect(self.makeCommandLine)
    
    def translateUI(self):
        self.setWindowTitle(app.caption(_("Engrave custom")))
        self.versionLabel.setText(_("LilyPond Version:"))
        self.outputLabel.setText(_("Output Format:"))
        self.resolutionLabel.setText(_("Resolution:"))
        self.modeLabel.setText(_("Engraving mode:"))
        self.modeCombo.setItemText(0, _("Preview"))
        self.modeCombo.setItemText(1, _("Publish"))
        self.modeCombo.setItemText(2, _("Layout Control"))
        self.englishCheck.setText(_("Run LilyPond with English messages"))
        self.deleteCheck.setText(_("Delete intermediate output files"))
        self.commandLineLabel.setText(_("Command line:"))
        self.buttons.button(QDialogButtonBox.Ok).setText(_("Run LilyPond"))
        self.outputCombo.update()
    
    def slotJobFinished(self, doc):
        if doc == self._document:
            self.buttons.button(QDialogButtonBox.Ok).setEnabled(True)
            self._document = None
    
    def setDocument(self, doc):
        self.selectLilyPondInfo(command.info(doc))
        if jobmanager.isRunning(doc):
            self._document = doc
            self.buttons.button(QDialogButtonBox.Ok).setEnabled(False)
        
    def loadLilyPondVersions(self):
        infos = lilypondinfo.infos() or [lilypondinfo.default()]
        infos.sort(key = lambda i: i.version() or (999,))
        self._infos = infos
        index = self.versionCombo.currentIndex()
        self.versionCombo.clear()
        for i in infos:
            icon = 'lilypond-run' if i.version() else 'dialog-error'
            self.versionCombo.addItem(icons.get(icon), i.prettyName())
        self.versionCombo.setCurrentIndex(index)
    
    def selectLilyPondInfo(self, info):
        if info in self._infos:
            self.versionCombo.setCurrentIndex(self._infos.index(info))
    
    def makeCommandLine(self):
        """Reads the widgets and builds a command line."""
        f = formats[self.outputCombo.currentIndex()]
        self.resolutionCombo.setEnabled('resolution' in f.widgets)
        cmd = ["$lilypond"]
        
        if self.modeCombo.currentIndex() == 0:   # preview mode
            cmd.append('-dpoint-and-click')
        elif self.modeCombo.currentIndex() == 1: # publish mode
            cmd.append('-dno-point-and-click')
        else:                                    # debug mode
            args = panelmanager.manager(self.parent()).layoutcontrol.widget().preview_options()
            cmd.extend(args)
        
        if self.deleteCheck.isChecked():
            cmd.append('-ddelete-intermediate-files')
        else:
            cmd.append('-dno-delete-intermediate-files')
        d = {
            'version': self._infos[self.versionCombo.currentIndex()].version,
            'resolution': self.resolutionCombo.currentText(),
        }
        cmd.append("$include")
        cmd.extend(f.options(d))
        cmd.append("$filename")
        self.commandLine.setText(' '.join(cmd))
    
    def getJob(self, document):
        """Returns a Job to start."""
        filename, includepath = documentinfo.info(document).jobinfo(True)
        i = self._infos[self.versionCombo.currentIndex()]
        cmd = []
        for t in self.commandLine.toPlainText().split():
            if t == '$lilypond':
                cmd.append(i.abscommand() or i.command)
            elif t == '$filename':
                cmd.append(filename)
            elif t == '$include':
                cmd.extend('-I' + path for path in includepath)
            else:
                cmd.append(t)
        j = job.Job()
        j.directory = os.path.dirname(filename)
        j.command = cmd
        if self.englishCheck.isChecked():
            j.environment['LANG'] = 'C'
        j.setTitle("{0} {1} [{2}]".format(
            os.path.basename(i.command), i.versionString(), document.documentName()))
        return j


Format = collections.namedtuple("Format", "type title options widgets")

formats = [
    Format(
        "pdf",
        lambda: _("PDF"),
        lambda d: ['--pdf'],
        (),
    ),
    Format(
        "ps",
        lambda: _("PostScript"),
        lambda d: ['--ps'],
        (),
    ),
    Format(
        "png",
        lambda: _("PNG"),
        lambda d: ['--png', '-dresolution={resolution}'.format(**d)],
        ('resolution',),
    ),
    Format(
        "svg",
        lambda: _("SVG"),
        lambda d: ['-dbackend=svg'],
        (),
    ),
    Format(
        "pdf",
        lambda: _("PDF (EPS Backend)"),
        lambda d: ['--pdf', '-dbackend=eps'],
        (),
    ),
    Format(
        "eps",
        lambda: _("Encapsulated PostScript (EPS Backend)"),
        lambda d: ['--ps', '-dbackend=eps'],
        (),
    ),
    Format(
        "png",
        lambda: _("PNG (EPS Backend)"),
        lambda d: ['--png', '-dbackend=eps', '-dresolution={resolution}'.format(**d)],
        ('resolution',),
    ),
]


