from PySide2.QtSql import QSqlDatabase, QSqlTableModel
from PySide2.QtWidgets import QApplication, QDateEdit
from PySide2.QtUiTools import QUiLoader
from PySide2.QtCore import QFile, Qt, QDateTime


class QtGui:
    def __init__(self, dbname):
        QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)  # to avoid a warning message in the terminal
        self.app = QApplication()
        db = QSqlDatabase.addDatabase("QSQLITE")
        db.setDatabaseName(dbname)
        db.open()

        self.edit_rating_window = EditRatingWindow(self.app)
        self.edit_settings_window = EditSettingsWindow(self.app)

    def execute_edit_ratings(self):
        self.edit_rating_window.show()

    def execute_edit_settings(self):
        self.edit_settings_window.show()


class EditRatingWindow:
    def __init__(self, app):
        self.app = app
        ui_file = QFile("edit_ratings.ui")
        ui_file.open(QFile.ReadOnly)

        loader = QUiLoader()
        self.window = loader.load(ui_file)
        ui_file.close()
        self.window.accepted.connect(self.process_accepted)

        self.model = QSqlTableModel()
        self.model.setTable("ratings")
        self.model.setEditStrategy(QSqlTableModel.OnFieldChange)

        self.date_edit_list = []

    def process_accepted(self):
        row_numbers = self.model.rowCount()
        for i in range(row_numbers):
            datestring = self.date_edit_list[i].date().toString("yyyy-MM-dd")
            record = self.model.record(i)
            record.setValue("expirationDate", datestring)
            self.model.setRecord(i, record)

    def show(self):
        self.model.select()
        row_numbers = self.model.rowCount()
        self.date_edit_list = []

        # delete all input fields from previous run
        # is there a better way
        # 'reversed' is necessary because removing changes item numbers
        layout = self.window.ratingsFrame.layout()
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            layout.removeItem(item)

        layout = self.window.otherRatingsFrame.layout()
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            layout.removeItem(item)

        layout = self.window.otherFrame.layout()
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            layout.removeItem(item)

        for i in range(row_numbers):
            title = self.model.record(i).value("title")
            date = self.model.record(i).value("expirationDate")
            self.date_edit_list.append(QDateEdit())
            self.date_edit_list[i].setDisplayFormat("dd.MM.yyyy")
            self.date_edit_list[i].setCalendarPopup(True)
            self.date_edit_list[i].setDate(QDateTime.fromString(date, "yyyy-MM-dd").date())
            if self.model.record(i).value("type") == "CR":
                self.window.ratingsFrame.layout().addRow(title, self.date_edit_list[i])
            if self.model.record(i).value("type") == "OR":
                self.window.otherRatingsFrame.layout().addRow(title, self.date_edit_list[i])
            if self.model.record(i).value("type") == "O":
                self.window.otherFrame.layout().addRow(title, self.date_edit_list[i])

        self.date_edit_list[0].setFocus()  # set focus to the first input field

        # TODO change to LineEdit + Validator + perhaps CalendarPopup
        # TODO add rating
        # TODO delete rating
        # TODO add additional fields

        self.window.show()
        self.app.exec_()


class EditSettingsWindow:
    def __init__(self, app):
        self.app = app
        ui_file = QFile("edit_settings.ui")
        ui_file.open(QFile.ReadOnly)

        loader = QUiLoader()
        self.window = loader.load(ui_file)
        ui_file.close()
        self.window.accepted.connect(self.process_accepted)

        self.model = QSqlTableModel()
        self.model.setTable("settings")
        self.model.setEditStrategy(QSqlTableModel.OnFieldChange)

    def process_accepted(self):
        # write changes to database
        self.model.select()  # just to be sure...
        row_numbers = self.model.rowCount()
        for i in range(row_numbers):
            record = self.model.record(i)
            if record.value('key') == 'default_PIC':
                record.setValue('value', self.window.defaultPICLineEdit.text())
            if record.value('key') == 'default_registration':
                record.setValue('value', self.window.defaultRegistrationLineEdit.text())
            if record.value('key') == 'default_airport':
                record.setValue('value', self.window.defaultAirportLineEdit.text())

            self.model.setRecord(i, record)

    def show(self):
        # populate fields with data in database
        self.model.select()
        row_count = self.model.rowCount()

        for i in range(row_count):
            if self.model.record(i).value("key") == 'default_PIC':
                self.window.defaultPICLineEdit.setText(self.model.record(i).value('value'))
            if self.model.record(i).value("key") == 'default_registration':
                self.window.defaultRegistrationLineEdit.setText(self.model.record(i).value('value'))
            if self.model.record(i).value("key") == 'default_airport':
                self.window.defaultAirportLineEdit.setText(self.model.record(i).value('value'))

        # select text in first input field
        self.window.defaultPICLineEdit.setFocus()
        self.window.defaultPICLineEdit.selectAll()

        self.window.show()
        self.app.exec_()
