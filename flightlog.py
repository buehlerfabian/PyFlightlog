#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Mar 21 14:03:50 2020

@author: fabi
"""

import sqlite3 as sq
import datetime as dt
import sys

# import tempfile
import requests

from dateutil.relativedelta import relativedelta
import csv

import cmd2
import argparse

import colorama as col

from flightlog_gui import QtGui


def to_datetime(diff):
    return dt.datetime.strptime("0000", "%H%M") + diff


def parse_dateparam(cmd, datestring):
    """Returns a datetime object"""
    # split given string at every "."
    if datestring is None:
        return dt.datetime.today().replace(hour=0, minute=0, second=0,
                                           microsecond=0)
    else:
        splitstring = datestring.split(".")

    # check if number of parts is correct
    if len(splitstring) != 3:
        cmd.perror("Start date must be given in the following"
                   " format: dd.mm.yyyy")
        return None

    # parse argument and create datetime object
    date1 = dt.datetime.strptime(
        splitstring[2] + "-" + splitstring[1] + "-" +
        splitstring[0], "%Y-%m-%d"
    )

    return date1


def create_connection(filename):
    """Creates and returns a database connection. If the given "
    "filename doesn't exist, a new file is created."""
    cn = sq.connect(filename)
    return cn


def create_tables():
    """Creates all necessary tables."""
    cur = con.cursor()
    cur_ap = con_ap.cursor()

    # check if tables exist
    cur.execute(
        "SELECT count(name) FROM sqlite_master WHERE type='table' "
        "AND name='flights'"
    )
    if cur.fetchone()[0] == 1:
        flights_db = True
    else:
        flights_db = False

    cur.execute(
        "SELECT count(name) FROM sqlite_master WHERE type='table' "
        "AND name='aircrafts'"
    )
    if cur.fetchone()[0] == 1:
        aircrafts_db = True
    else:
        aircrafts_db = False

    cur.execute(
        "SELECT count(name) FROM sqlite_master WHERE type='table' "
        "AND name='ratings'"
    )
    if cur.fetchone()[0] == 1:
        ratings_db = True
    else:
        ratings_db = False

    cur.execute(
        "SELECT count(name) FROM sqlite_master WHERE type='table' "
        "AND name='settings'"
    )
    if cur.fetchone()[0] == 1:
        settings_db = True
    else:
        settings_db = False

    cur_ap.execute(
        "SELECT count(name) FROM sqlite_master WHERE type='table' "
        "AND name='airports'"
    )
    if cur_ap.fetchone()[0] == 1:
        airports_db = True
    else:
        airports_db = False

    # create missing tables
    if not flights_db:
        cur.execute(
            "create table flights (id integer primary key, "
            "flightdate string, type string, "
            "registration string, departureId string, destinationId string,"
            "offblock string, onblock string, "
            "startTime string, landingTime string,"
            "landingsDay integer, landingsNight integer, "
            "picName string, pilotFunction string,"
            "flightTimeNight integer, flightTimeIFR integer, "
            "flightTimeClass string, studentName string, "
            "guests string, remarks string, internalMarkers string)"
        )

    if not aircrafts_db:
        cur.execute(
            "create table aircrafts (registration string primary key, "
            "type string, class string)"
        )

    if not ratings_db:
        cur.execute(
            "create table ratings (id integer primary key, "
            "title string, expirationDate string, "
            "warningPeriod string, renewalConditions string, type string)"
        )
        cur.execute(
            "insert into ratings values (?,?, ?, ?, ?, ?)",
            ("1", "SEP", "2000-01-01", "m3", "", "CR"),
        )

    if not settings_db:
        cur.execute("create table settings (key string primary key, "
                    "value string)")
        cur.execute("insert into settings values (?, ?)",
                    ("default_PIC", "Bühler"))
        cur.execute(
            "insert into settings values (?, ?)",
            ("default_registration", "DESFM")
        )
        cur.execute("insert into settings values (?, ?)",
                    ("default_airport", "EDTM"))

    if not airports_db:
        cur_ap.execute(
            "create table airports (icaoId string primary key, "
            "name string, lat string, "
            "long string, elev string)"
        )

    con.commit()
    con_ap.commit()


def delete_table():
    """Deletes the table if it exists."""
    cur = con.cursor()
    cur.execute("drop table if exists flights")
    cur.execute("drop table if exists ratings")
    cur.execute("drop table if exists aircrafts")
    cur.execute("drop table if exists settings")
    con.commit()


def add_flight(
    ofbt,
    stt,
    ldt,
    onbt,
    flightdate=None,
    registration=None,
    apdep=None,
    apdest=None,
    ldgd=1,
    ldgn="",
    pic=None,
    pfct=None,
    ftn=None,
    ftifr=None,
    stud=None,
    guests=None,
    rmk=None,
):
    """Adds a flight."""

    cur = con.cursor()

    # get defaults from database
    cur.execute("select value from settings where key='default_PIC'")
    result = cur.fetchone()
    default_pic = result["value"]

    cur.execute("select value from settings where key='default_registration'")
    result = cur.fetchone()
    default_registration = result["value"]

    cur.execute("select value from settings where key='default_airport'")
    result = cur.fetchone()
    default_airport = result["value"]

    # set missing flightdate
    if flightdate is None:
        flightdate = dt.date.today()

    # set missing aircraft
    if registration is None:
        registration = default_registration

    # get aircraft type and class from aircraft database

    cur.execute("select * from aircrafts where registration=?",
                (registration,))
    result = cur.fetchone()

    # Aircraft not found?
    if result is None:
        print(
            col.Fore.RED
            + f"Aircraft not found: {registration}. Check callsign "
            "and add aircraft if necessary."
            + col.Style.RESET_ALL
        )
        return

    actype, ftc = (result[1], result[2])

    # set missing airport of departure
    if apdep is None:
        apdep = default_airport

    # set missing airport of destination
    if apdest is None:
        apdest = default_airport

    # set missing PIC
    if pic is None:
        pic = default_pic

    # set missing pilot function
    if pfct is None:
        pfct = "PIC"

    # set missing night flight time
    if ftn is None:
        ftn = ""

    # set missing ifr flight time
    if ftifr is None:
        ftifr = ""

    # set missing student
    if stud is None:
        stud = ""

    # set missing guests
    if guests is None:
        guests = ""

    # set missing remarks
    if rmk is None:
        rmk = ""

    # insert flight into database
    cur.execute(
        "insert into flights (flightdate, type, registration, "
        "departureId, destinationId, offblock, "
        "onblock, startTime, landingTime, "
        "landingsDay, landingsNight, picName, "
        "pilotFunction, flightTimeNight, "
        "flightTimeIFR, flightTimeClass, "
        "studentName, guests, remarks) values"
        " (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
        " ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            flightdate,
            actype,
            registration,
            apdep,
            apdest,
            ofbt,
            onbt,
            stt,
            ldt,
            ldgd,
            ldgn,
            pic,
            pfct,
            ftn,
            ftifr,
            ftc,
            stud,
            guests,
            rmk,
        ),
    )
    con.commit()


def import_database(filename):
    """Import a database from a csv file."""
    with open(filename) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=",")
        for row in csv_reader:
            # noinspection PyTypeChecker
            add_flight(
                ofbt=row[4],
                stt=row[5],
                ldt=row[8],
                onbt=row[7],
                registration=row[2],
                apdep=row[3],
                flightdate=dt.datetime.strptime(row[0], "%d.%m.%y").strftime(
                    "%Y-%m-%d"
                ),
                apdest=row[6],
                ldgd=row[12],
                ldgn=row[13],
                pfct=row[16],
                pic="Bühler" if row[9] == "*" else row[9],
                ftn=row[17],
                ftifr=row[18],
                guests=row[11],
                rmk=row[19],
                stud="Bühler" if row[10] == "*" else row[10],
            )


class CmdApp(cmd2.Cmd):
    """Command application object, manages all the cli stuff"""

    def __init__(self):
        # some initializations
        super().__init__()
        del cmd2.Cmd.do_edit
        del cmd2.Cmd.do_py
        del cmd2.Cmd.do_run_pyscript
        del cmd2.Cmd.do_run_script
        del cmd2.Cmd.do_set
        del cmd2.Cmd.do_shortcuts
        del cmd2.Cmd.do_macro
        del cmd2.Cmd.do_shell
        del cmd2.Cmd.do_alias
        self.prompt = (
            col.Fore.CYAN + col.Style.BRIGHT +
            db_name + " > " + col.Style.RESET_ALL
        )

        # noinspection PyTypeChecker
        self.do_stat("")
        # noinspection PyTypeChecker
        self.do_check("--hide-valid")

    def parse_dateparams(self, datestring_start, datestring_end):
        """Returns a tuple (start_date, end_date) of datetime objects
        if end date is left out, it will be set to
        * end of day, if start_date has format dd.mm.yyyy
        * end of month, if start_date has format mm.yyyy
        * end of year, if start_date has format yyyy
        relative start dates:
        dNNN: NNN days before end date / today
        mNN: NN months before end date / today
        yNN: NN years before end date / today"""

        start_date = None
        end_date = None

        # check if start date is relative or absolute
        if datestring_start[0] in ["d", "m", "y"]:
            mode_char = datestring_start[0]
            num = int(datestring_start[1:])
            # set end date and preliminary start date
            if datestring_end == "today" or datestring_end is None:
                end_date = dt.datetime.today().replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                start_date = end_date
                end_date = end_date + relativedelta(days=1)
            else:
                # split given string at every "."
                splitstring = datestring_end.split(".")

                # check if number of parts is correct
                if len(splitstring) != 3:
                    self.perror(
                        "End date must be given in the "
                        "following format: dd.mm.yyyy"
                    )
                    return None

                end_date = dt.datetime.strptime(
                    splitstring[2] + "-" + splitstring[1] + "-" +
                    splitstring[0], "%Y-%m-%d",
                )
                start_date = end_date
                end_date = end_date + relativedelta(days=1)

            # shift start date according to options
            if mode_char == "d":
                start_date += relativedelta(days=-num)
            if mode_char == "m":
                start_date += relativedelta(months=-num)
            if mode_char == "y":
                start_date += relativedelta(years=-num)

        else:
            # split given string at every "."
            splitstring = datestring_start.split(".")

            # check if number of parts is in the correct range (1 to 3)
            if len(splitstring) > 3:
                self.perror(
                    "Start date must be 'today' or given in one of the "
                    "following formats: yyyy / mm.yyyy / "
                    "dd.mm.yyyy"
                )
                return None

            # parse argument and create datetime object

            if len(splitstring) == 1:
                start_date = dt.datetime.strptime(splitstring[0], "%Y")
                end_date = start_date + relativedelta(years=1)

            if len(splitstring) == 2:
                start_date = dt.datetime.strptime(
                    splitstring[1] + "-" + splitstring[0], "%Y-%m"
                )
                end_date = start_date + relativedelta(months=1)

            if len(splitstring) == 3:
                start_date = dt.datetime.strptime(
                    splitstring[2] + "-" + splitstring[1] + "-" +
                    splitstring[0], "%Y-%m-%d",
                )
                end_date = start_date + relativedelta(days=1)

                # if end_date is given explicitly, override calculated end_date
            if datestring_end is not None:
                # check if it is 'today'
                if datestring_end == "today":
                    end_date = dt.datetime.today().replace(
                        hour=0, minute=0, second=0, microsecond=0
                    )
                    end_date = end_date + relativedelta(days=1)
                else:
                    # split given string at every "."
                    splitstring = datestring_end.split(".")

                    # check if number of parts is in the correct range (1 to 3)
                    if len(splitstring) > 3:
                        self.perror(
                            "End date must be given in one of the following "
                            "formats: yyyy / mm.yyyy / "
                            "dd.mm.yyyy"
                        )
                        return None

                    if len(splitstring) == 1:
                        end_date = dt.datetime.strptime(splitstring[0], "%Y")
                        end_date = end_date + relativedelta(years=1)

                    if len(splitstring) == 2:
                        end_date = dt.datetime.strptime(
                            splitstring[1] + "-" + splitstring[0], "%Y-%m"
                        )
                        end_date = end_date + relativedelta(months=1)

                    if len(splitstring) == 3:
                        end_date = dt.datetime.strptime(
                            splitstring[2]
                            + "-"
                            + splitstring[1]
                            + "-"
                            + splitstring[0],
                            "%Y-%m-%d",
                        )
                        end_date = end_date + relativedelta(days=1)
        return start_date, end_date

    # parser for add command
    parser_add = argparse.ArgumentParser()
    parser_add.add_argument("ofbt", help="offblock time")
    parser_add.add_argument("stt", help="time of actual takeoff")
    parser_add.add_argument("ldt", help="time of actual landing")
    parser_add.add_argument("onbt", help="onblock time")
    dategroup = parser_add.add_mutually_exclusive_group()
    dategroup.add_argument(
        "-d",
        "--days-before",
        nargs=1,
        type=int,
        dest="days",
        help="date of flight is specified number of days before today",
    )
    dategroup.add_argument(
        "--date",
        nargs=1,
        dest="date",
        help="specify date of flight in format dd.mm.yyyy",
    )
    parser_add.add_argument(
        "-a", "--aircraft", nargs=1, dest="acft",
        help="specify aicraft by registration"
    )
    parser_add.add_argument(
        "-dep",
        "--departure",
        nargs=1,
        dest="apdep",
        help="specify airport of departure",
    )
    parser_add.add_argument(
        "-dest",
        "--destination",
        nargs=1,
        dest="apdest",
        help="specify airport of destination",
    )
    parser_add.add_argument(
        "-l",
        "--landings-day",
        nargs=1,
        type=int,
        dest="ldgd",
        help="specify number of day landings",
    )
    parser_add.add_argument(
        "-ln",
        "--landings-night",
        nargs=1,
        type=int,
        dest="ldgn",
        help="specify number of night landings",
    )
    parser_add.add_argument(
        "-p",
        "--pic",
        nargs=1,
        dest="pic",
        help="specify PIC; if used, --pilot-function must also be given",
    )
    parser_add.add_argument(
        "-pf",
        "--pilot-function",
        nargs=1,
        dest="pfct",
        help="specify pilot function, i.e. PIC, Dual",
    )
    parser_add.add_argument(
        "-n",
        "--night",
        action="store_true",
        dest="night",
        help="use full flight time as night flight time, "
        "set all landings as night landings",
    )
    parser_add.add_argument(
        "-i",
        "--ifr",
        action="store_true",
        dest="ifr",
        help="use full flight time as ifr flight time",
    )
    parser_add.add_argument(
        "-g", "--guests", dest="guests", nargs=1, help="specify guests"
    )
    parser_add.add_argument(
        "-r", "--remarks", dest="rmk", nargs=1, help="specify remarks"
    )
    parser_add.add_argument(
        "-fi",
        "--flight-instruction",
        dest="fi",
        nargs=1,
        help="set pilot function to FI, argument sets student",
    )
    parser_add.add_argument(
        "--night-time", nargs=1, dest="ftn", help="specify night flight time"
    )
    parser_add.add_argument(
        "--ifr-time", nargs=1, dest="ftifr", help="specify ifr flight time"
    )
    parser_add.add_argument("--student", dest="stud", nargs=1,
                            help="specify student")

    @cmd2.with_argparser(parser_add)
    def do_add(self, args):
        """Adds a flight."""
        ofbt = dt.datetime.strptime(args.ofbt, "%H%M")
        ofbt_string = ofbt.strftime("%H:%M")
        stt_string = dt.datetime.strptime(args.stt, "%H%M").strftime("%H:%M")
        ldt_string = dt.datetime.strptime(args.ldt, "%H%M").strftime("%H:%M")
        onbt = dt.datetime.strptime(args.onbt, "%H%M")
        onbt_string = onbt.strftime("%H:%M")

        flightdate = dt.date.today()
        # option --days-before specified
        if args.days:
            flightdate -= dt.timedelta(args.days[0])
        # option --date specified
        if args.date:
            flightdate = dt.datetime.strptime(args.date[0], "%d.%m.%Y")

            # option --aircraft specified
        aircraft = None
        if args.acft:
            aircraft = args.acft[0]

        # option --departure specified
        apdep = None
        if args.apdep:
            apdep = args.apdep[0]

        # option --departure specified
        apdest = None
        if args.apdest:
            apdest = args.apdest[0]

        # option --landings_day specified
        ldgd = 1
        if args.ldgd:
            ldgd = args.ldgd[0]

        # option --landings_night specified
        ldgn = ""
        if args.ldgn:
            ldgn = args.ldgn[0]
            if not args.ldgd:
                ldgd = ""

        # option --pic specified
        pic = None
        if args.pic:
            pic = args.pic[0]
            if (pic != "Bühler") and not args.pfct:
                self.perror(
                    "If another PIC is specified, option --pilot-function "
                    "must be given."
                )
                return

        # option --pilot_function specified
        pfct = None
        if args.pfct:
            pfct = args.pfct[0]

        # option --night-time specified
        ftn_string = None
        if args.ftn:
            ftn_string = dt.datetime.strptime(args.ftn[0],
                                              "%H%M").strftime("%H:%M")

        # option --ifr-time specified
        ftifr_string = None
        if args.ftifr:
            ftifr_string = dt.datetime.strptime(args.ftifr[0],
                                                "%H%M").strftime("%H:%M")

        # option --student specified
        stud = None
        if args.stud:
            stud = args.stud[0]

        # option --guests specified
        guests = None
        if args.guests:
            guests = args.guests[0]

        # option --remarks specified
        rmk = None
        if args.rmk:
            rmk = args.rmk[0]

        # option --night given
        if args.night:
            if ldgd != "":
                if ldgn != "":
                    ldgn += ldgd
                else:
                    ldgn = ldgd
                ldgd = ""
            ftn_string = to_datetime(onbt - ofbt).strftime("%H:%M")

        # option --ifr given
        if args.ifr:
            ftifr_string = to_datetime(onbt - ofbt).strftime("%H:%M")

        # option --flight_instruction specified
        if args.fi:
            if args.pfct:
                self.perror(
                    "Options --flight_instruction and --pilot_function cannot"
                    " be used together."
                )
                return
            if args.pic:
                self.perror(
                    "Options --flight_instruction and --pic cannot "
                    "be used together."
                )
            pfct = "FI"
            stud = args.fi[0]

        # add flight to database
        add_flight(
            ofbt_string,
            stt_string,
            ldt_string,
            onbt_string,
            flightdate=flightdate.strftime("%Y-%m-%d"),
            registration=aircraft,
            apdep=apdep,
            apdest=apdest,
            ldgd=ldgd,
            ldgn=ldgn,
            pic=pic,
            pfct=pfct,
            ftn=ftn_string,
            ftifr=ftifr_string,
            stud=stud,
            guests=guests,
            rmk=rmk,
        )

        # show added flight
        self.show_delete(flightdate)

    # parser for last command
    parser_last = argparse.ArgumentParser()
    parser_last.add_argument(
        "num", nargs="?", type=int, default=5, help="Show last num flights."
    )
    parser_last.add_argument(
        "-l", "--long", action="store_true", dest="long",
        help="show all data fields"
    )

    @cmd2.with_argparser(parser_last)
    def do_last(self, args):
        """Lists the last n flights."""
        cur = con.cursor()
        cur.execute(
            "select * from (select flightdate, type, registration, "
            "departureId, destinationId, offblock, "
            "onblock, startTime, landingTime, landingsDay, "
            "landingsNight, landingsDay+landingsNight, "
            "picName,pilotFunction, flightTimeNight, flightTimeIFR, "
            "flightTimeClass, studentName, guests, "
            "remarks from flights order by flightdate desc, "
            "offblock desc limit ?) "
            "order by flightdate asc, offblock asc;",
            (args.num,),
        )
        if not args.long:
            for result in cur:
                date = dt.datetime.strptime(result["flightdate"],
                                            "%Y-%m-%d").strftime(
                    "%d.%m.%Y"
                )
                self.poutput(
                    "{:<11}{:>6}  {:>4} {:>4}  {:>4} {:>4} {:>2} Ldg".format(
                        date,
                        result["registration"],
                        result["departureId"],
                        result["offblock"],
                        result["destinationId"],
                        result["onblock"],
                        result["landingsDay+landingsNight"],
                    )
                )
        else:
            for result in cur:
                date = dt.datetime.strptime(result["flightdate"],
                                            "%Y-%m-%d").strftime(
                    "%d.%m.%Y"
                )
                self.poutput(
                    "{:<11}{:>6} {:>5} {:>4} {:>4} {:>4}  {:>4} {:>4} "
                    "{:>4} {:>2}/{:>2} Ldg(day/night)"
                    "  {}({}) {} {}".format(
                        date,
                        result["type"],
                        result["registration"],
                        result["departureId"],
                        result["offblock"],
                        result["startTime"],
                        result["destinationId"],
                        result["landingTime"],
                        result["onblock"],
                        result["landingsDay"],
                        result["landingsNight"],
                        result["picName"],
                        result["pilotFunction"],
                        result["studentName"],
                        result["guests"],
                    )
                )

    # parser for add-aircraft command
    parser_add_aircraft = argparse.ArgumentParser()
    parser_add_aircraft.add_argument(
        "registration", help="specify aircraft registration"
    )
    parser_add_aircraft.add_argument("type", help="specify aircraft type")
    parser_add_aircraft.add_argument(
        "acft_class", help="specify aircraft class, i.e. SEP"
    )

    @cmd2.with_argparser(parser_add_aircraft)
    def do_add_aircraft(self, args):
        """Adds an aircraft."""
        cur = con.cursor()
        cur.execute(
            "insert into aircrafts (registration, type, class) values"
            " (?, ?, ?)",
            (args.registration, args.type, args.acft_class),
        )
        con.commit()

    # parser for ls command
    parser_ls = argparse.ArgumentParser()

    parser_ls.add_argument(
        "start_date",
        help="start date as yyyy or mm.yyyy or dd.mm.yyyy or "
        "relative as 'dNNN', 'mNN', 'yNN' "
        "where N are digits",
    )

    parser_ls.add_argument(
        "end_date",
        nargs="?",
        help="end date as yyyy or mm.yyyy or dd.mm.yyyy "
        "or 'today'; in case of "
        "relative start date dd.mm.yyyy is mandatory",
    )
    parser_ls.add_argument(
        "-l", "--long", action="store_true", dest="long",
        help="show all data fields"
    )
    parser_ls.add_argument(
        "-dep", "--departure", nargs=1, dest="apdep",
        help="filter airport of departure"
    )
    parser_ls.add_argument(
        "-dest",
        "--destination",
        nargs=1,
        dest="apdest",
        help="filter airport of destination",
    )
    parser_ls.add_argument(
        "-a", "--aircraft", nargs=1, dest="acft",
        help="filter aircraft registration"
    )
    parser_ls.add_argument(
        "-t", "--type", nargs=1, dest="type", help="filter aircraft type"
    )
    parser_ls.add_argument(
        "-c", "--class", nargs=1, dest="aclass", help="filter aircraft class"
    )
    parser_ls.add_argument("-p", "--pic", nargs=1, dest="pic",
                           help="filter PIC")
    parser_ls.add_argument(
        "-pf",
        "--pilot-function",
        nargs=1,
        dest="pfct",
        help="filter pilot function, i.e. PIC, Dual",
    )
    parser_ls.add_argument(
        "-s", "--student", dest="stud", nargs=1, help="filter student"
    )
    parser_ls.add_argument(
        "-g", "--guests", dest="guests", nargs=1, help="filter guests"
    )
    parser_ls.add_argument(
        "-r", "--remarks", dest="rmk", nargs=1, help="filter remarks"
    )
    parser_ls.add_argument(
        "-fi",
        "--flight-instruction",
        dest="fi",
        action="store_true",
        help="filter pilot function to FI",
    )

    @cmd2.with_argparser(parser_ls)
    def do_ls(self, args):
        """Lists all flights in a given date range."""
        start_date, end_date = self.parse_dateparams(args.start_date,
                                                     args.end_date)

        # retrieve flights from database
        cur = con.cursor()

        # parse filter options and set conditions accordingly
        conditions = ""
        if args.apdep:
            conditions += f"and departureId='{args.apdep[0]}' "
        if args.apdest:
            conditions += f"and destinationId='{args.apdest[0]}' "
        if args.acft:
            conditions += f"and registration='{args.acft[0]}' "
        if args.type:
            conditions += f"and type='{args.type[0]}' "
        if args.aclass:
            conditions += f"and flightTimeClass='{args.aclass[0]}' "
        if args.pic:
            conditions += f"and picName='{args.pic[0]}' "
        if args.pfct:
            conditions += f"and pilotFunction='{args.pfct[0]}' "
        if args.stud:
            conditions += f"and studentName like '%{args.stud[0]}%' "
        if args.guests:
            conditions += f"and guests like '%{args.guests[0]}%' "
        if args.rmk:
            conditions += f"and remarks like '%{args.rmk[0]}%' "
        if args.fi:
            conditions += "and pilotFunction='FI'"

        if conditions == "":
            conditions = "and True"  # no additional condition was given

        query_string = (
            "select flightdate, type, registration, "
            "departureId, destinationId, offblock, "
            "onblock, startTime, landingTime, landingsDay, "
            "landingsNight, landingsDay+landingsNight, "
            "picName,pilotFunction, flightTimeNight, flightTimeIFR, "
            "flightTimeClass, studentName, guests, "
            "remarks from flights where flightdate >= ? and flightdate < ? "
            + conditions
            + " order by flightdate asc, offblock asc"
        )

        cur.execute(
            query_string,
            (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")),
        )

        # print results
        if not args.long:
            for result in cur:
                date = dt.datetime.strptime(result["flightdate"],
                                            "%Y-%m-%d").strftime(
                    "%d.%m.%Y"
                )
                self.poutput(
                    "{:<11}{:>6}  {:>4} {:>4}  {:>4} {:>4} {:>2} Ldg".format(
                        date,
                        result["registration"],
                        result["departureId"],
                        result["offblock"],
                        result["destinationId"],
                        result["onblock"],
                        result["landingsDay+landingsNight"],
                    )
                )
        else:
            for result in cur:
                date = dt.datetime.strptime(result["flightdate"],
                                            "%Y-%m-%d").strftime(
                    "%d.%m.%Y"
                )
                self.poutput(
                    "{:<11}{:>6} {:>5} {:>4} {:>4} {:>4}  {:>4} "
                    "{:>4} {:>4} {:>2}/{:>2} Ldg(day/night)"
                    "  {}({}) {} {}".format(
                        date,
                        result["type"],
                        result["registration"],
                        result["departureId"],
                        result["offblock"],
                        result["startTime"],
                        result["destinationId"],
                        result["landingTime"],
                        result["onblock"],
                        result["landingsDay"],
                        result["landingsNight"],
                        result["picName"],
                        result["pilotFunction"],
                        result["studentName"],
                        result["guests"],
                    )
                )

    # parser for show command
    parser_show = argparse.ArgumentParser()
    parser_show.add_argument(
        "date", nargs="?", help="date as dd.mm.yyyy, default is today"
    )

    @cmd2.with_argparser(parser_show)
    def do_show(self, args):
        """Shows all data fields of the flight(s) of a given day."""

        date = parse_dateparam(self, args.date)
        self.show_delete(date)

    def show_delete(self, date, do_delete=False):
        """Common function called by do_show and do_delete"""
        # retrieve flights from database
        cur = con.cursor()
        cur.execute(
            "select flightdate, type, registration, "
            "departureId, destinationId, offblock, "
            "onblock, startTime, landingTime, landingsDay, "
            "landingsNight, landingsDay+landingsNight, "
            "picName,pilotFunction, flightTimeNight, "
            "flightTimeIFR, flightTimeClass, studentName, guests, "
            "remarks, id from flights where flightdate ="
            " ? order by offblock asc ",
            (date.strftime("%Y-%m-%d"),),
        )

        res = cur.fetchall()
        # close cursor to prevent any conflict with deleting a record
        # while looping through the result list
        # no idea if this is necessary
        cur.close()
        cur = con.cursor()  # get a shiny new cursor

        for result in res:
            date = dt.datetime.strptime(result["flightdate"],
                                        "%Y-%m-%d").strftime(
                "%d.%m.%Y"
            )
            self.poutput()

            s1 = "{:>15} ".format("Date:")
            s2 = "{}".format(date)
            self.poutput(col.Fore.GREEN + s1 + col.Style.RESET_ALL + s2)

            s1 = "{:>15} ".format("Aircraft type:")
            s2 = "{:10}".format(result["type"])
            s3 = "{:>7} ".format("Class:")
            s4 = "{:>5}".format(result["flightTimeClass"])
            self.poutput(
                col.Fore.GREEN
                + s1
                + col.Style.RESET_ALL
                + s2
                + col.Fore.GREEN
                + s3
                + col.Style.RESET_ALL
                + s4
            )

            s1 = "{:>15} ".format("Registration:")
            s2 = "{}".format(result["registration"])
            self.poutput(col.Fore.GREEN + s1 + col.Style.RESET_ALL + s2)

            s1 = "{:>15} ".format("Departed at:")
            s2 = "{:7}".format(result["departureId"])
            s3 = "{:>12} ".format("Offblock:")
            s4 = "{:7}".format(result["offblock"])
            s5 = "{:>12} ".format("Start:")
            s6 = "{:7}".format(result["startTime"])
            self.poutput(
                col.Fore.GREEN
                + s1
                + col.Style.RESET_ALL
                + s2
                + col.Fore.GREEN
                + s3
                + col.Style.RESET_ALL
                + s4
                + col.Fore.GREEN
                + s5
                + col.Style.RESET_ALL
                + s6
            )

            s1 = "{:>15} ".format("Landed at:")
            s2 = "{:7}".format(result["destinationId"])
            s3 = "{:>12} ".format("Landing:")
            s4 = "{:7}".format(result["landingTime"])
            s5 = "{:>12} ".format("Onblock:")
            s6 = "{:7}".format(result["onblock"])
            self.poutput(
                col.Fore.GREEN
                + s1
                + col.Style.RESET_ALL
                + s2
                + col.Fore.GREEN
                + s3
                + col.Style.RESET_ALL
                + s4
                + col.Fore.GREEN
                + s5
                + col.Style.RESET_ALL
                + s6
            )

            s1 = "{:>15} ".format("Flight time:")

            diff = dt.datetime.strptime(
                result["onblock"], "%H:%M"
            ) - dt.datetime.strptime(result["offblock"], "%H:%M")

            s2 = to_datetime(diff).strftime("%H:%M")
            s3 = "{:>7}".format(" IFR:")
            s4 = "{:7}".format(result["flightTimeIFR"])
            s5 = "{:>7}".format(" night:")
            s6 = "{:7}".format(result["flightTimeNight"])
            self.poutput(
                col.Fore.GREEN
                + s1
                + col.Style.RESET_ALL
                + s2
                + col.Fore.GREEN
                + s3
                + col.Style.RESET_ALL
                + s4
                + col.Fore.GREEN
                + s5
                + col.Style.RESET_ALL
                + s6
            )

            s1 = "{:>10}{:>5}".format("Landings", "day:")
            s2 = "{:>2} ".format(result["landingsDay"])
            s3 = "{:>7}".format("night:")
            s4 = "{:>2} ".format(result["landingsNight"])
            self.poutput(
                col.Fore.GREEN
                + s1
                + col.Style.RESET_ALL
                + s2
                + col.Fore.GREEN
                + s3
                + col.Style.RESET_ALL
                + s4
            )

            s1 = "{:>15} ".format("PIC:")
            s2 = "{}".format(result["picName"])
            self.poutput(col.Fore.GREEN + s1 + col.Style.RESET_ALL + s2)

            if result["pilotFunction"] != "FI":
                s1 = "{:>15} ".format("Logging as:")
                s2 = "{}".format(result["pilotFunction"])
                self.poutput(col.Fore.GREEN + s1 + col.Style.RESET_ALL + s2)
            else:
                s1 = "{:>15} ".format("Logging as:")
                s2 = "{}   ".format(result["pilotFunction"])
                s3 = "Student: "
                s4 = "{}".format(result["studentName"])
                self.poutput(
                    col.Fore.GREEN
                    + s1
                    + col.Style.RESET_ALL
                    + s2
                    + col.Fore.GREEN
                    + s3
                    + col.Style.RESET_ALL
                    + s4
                )

            s1 = "{:>15} ".format("Guests:")
            s2 = "{}".format(result["guests"])
            self.poutput(col.Fore.GREEN + s1 + col.Style.RESET_ALL + s2)

            s1 = "{:>15} ".format("Remarks:")
            s2 = "{}".format(result["remarks"])
            self.poutput(col.Fore.GREEN + s1 + col.Style.RESET_ALL + s2)

            # ask for deletion if in delete mode
            if do_delete:
                ans = self.read_input("Delete this flight (y/N)? ")
                if ans == "y" or ans == "Y":
                    idn = result["id"]
                    cur.execute("delete from flights where id=? limit 1",
                                (int(idn),))
                    con.commit()
                    self.poutput(f"Flight Nr. {int(idn)} has been deleted.")

    # parser for delete command
    parser_delete = argparse.ArgumentParser()
    parser_delete.add_argument(
        "date", nargs="?", help="date as dd.mm.yyyy, default is today"
    )

    @cmd2.with_argparser(parser_delete)
    def do_delete(self, args):
        """Shows all flights of a given day and offers option to delete."""
        date = parse_dateparam(self, args.date)
        self.show_delete(date, do_delete=True)

    # parser for sum command
    parser_sum = argparse.ArgumentParser()
    parser_sum.add_argument(
        "start_date",
        help="start date as yyyy or mm.yyyy or dd.mm.yyyy or "
        "relative as 'dNNN', 'mNN', 'yNN' "
        "where N are digits",
    )
    parser_sum.add_argument(
        "end_date",
        nargs="?",
        help="end date as yyyy or mm.yyyy or dd.mm.yyyy "
        "or 'today'; in case of "
        "relative start date dd.mm.yyyy is mandatory",
    )
    parser_sum.add_argument(
        "-l", "--long", action="store_true", dest="long",
        help="show all data fields"
    )
    parser_sum.add_argument(
        "-dep", "--departure", nargs=1, dest="apdep",
        help="filter airport of departure"
    )
    parser_sum.add_argument(
        "-dest",
        "--destination",
        nargs=1,
        dest="apdest",
        help="filter airport of destination",
    )
    parser_sum.add_argument(
        "-a", "--aircraft", nargs=1, dest="acft",
        help="filter aircraft registration"
    )
    parser_sum.add_argument(
        "-t", "--type", nargs=1, dest="type", help="filter aircraft type"
    )
    parser_sum.add_argument(
        "-c", "--class", nargs=1, dest="aclass", help="filter aircraft class"
    )
    parser_sum.add_argument("-p", "--pic", nargs=1,
                            dest="pic", help="filter PIC")
    parser_sum.add_argument(
        "-pf",
        "--pilot-function",
        nargs=1,
        dest="pfct",
        help="filter pilot function, i.e. PIC, Dual",
    )
    parser_sum.add_argument(
        "-s", "--student", dest="stud", nargs=1, help="filter student"
    )
    parser_sum.add_argument(
        "-g", "--guests", dest="guests", nargs=1, help="filter guests"
    )
    parser_sum.add_argument(
        "-r", "--remarks", dest="rmk", nargs=1, help="filter remarks"
    )
    parser_sum.add_argument(
        "-fi",
        "--flight-instruction",
        dest="fi",
        action="store_true",
        help="filter pilot function to FI",
    )

    @cmd2.with_argparser(parser_sum)
    def do_sum(self, args):
        """Calculates sums of times and landings in given date range."""
        start_date, end_date = self.parse_dateparams(args.start_date,
                                                     args.end_date)

        cur = con.cursor()

        # parse filter options and set conditions accordingly
        conditions = ""
        if args.apdep:
            conditions += f"and departureId='{args.apdep[0]}' "
        if args.apdest:
            conditions += f"and destinationId='{args.apdest[0]}' "
        if args.acft:
            conditions += f"and registration='{args.acft[0]}' "
        if args.type:
            conditions += f"and type='{args.type[0]}' "
        if args.aclass:
            conditions += f"and flightTimeClass='{args.aclass[0]}' "
        if args.pic:
            conditions += f"and picName='{args.pic[0]}' "
        if args.pfct:
            conditions += f"and pilotFunction='{args.pfct[0]}' "
        if args.stud:
            conditions += f"and studentName like '%{args.stud[0]}%' "
        if args.guests:
            conditions += f"and guests like '%{args.guests[0]}%' "
        if args.rmk:
            conditions += f"and remarks like '%{args.rmk[0]}%' "
        if args.fi:
            conditions += "and pilotFunction='FI'"

        if conditions == "":
            conditions = "and True"  # no additional condition was given

        # retrieve flights from database
        query_string = (
            "select flightdate, type, registration, "
            "departureId, destinationId, offblock, "
            "onblock, startTime, landingTime, landingsDay, "
            "landingsNight, landingsDay+landingsNight, "
            "picName,pilotFunction, flightTimeNight, "
            "flightTimeIFR, flightTimeClass, studentName, guests, "
            "remarks from flights where flightdate >= ? and flightdate < ? "
            + conditions
            + " order by flightdate asc, offblock asc"
        )
        cur.execute(
            query_string,
            (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")),
        )

        # loop over all flights and do the sums
        block_sec = 0
        flight_sec = 0
        night_sec = 0
        ifr_sec = 0
        ldg_day = 0
        ldg_night = 0
        for result in cur:
            diff = dt.datetime.strptime(
                result["onblock"], "%H:%M"
            ) - dt.datetime.strptime(result["offblock"], "%H:%M")
            if diff.total_seconds() >= 0:
                block_sec += diff.total_seconds()
            else:
                block_sec += diff.total_seconds() + 86400  # add 24h = 86400 s

            diff = dt.datetime.strptime(
                result["landingTime"], "%H:%M"
            ) - dt.datetime.strptime(result["startTime"], "%H:%M")
            if diff.total_seconds() >= 0:
                flight_sec += diff.total_seconds()
            else:
                flight_sec += diff.total_seconds() + 86400  # add 24h = 86400 s

            if result["flightTimeNight"] != "":
                diff = dt.datetime.strptime(
                    result["flightTimeNight"], "%H:%M"
                ) - dt.datetime.strptime("00:00", "%H:%M")
                night_sec += diff.total_seconds()

            if result["flightTimeIFR"] != "":
                diff = dt.datetime.strptime(
                    result["flightTimeIFR"], "%H:%M"
                ) - dt.datetime.strptime("00:00", "%H:%M")
                ifr_sec += diff.total_seconds()

            if result["landingsDay"] != "":
                ldg_day += int(result["landingsDay"])

            if result["landingsNight"] != "":
                ldg_night += int(result["landingsNight"])

        block_min, block_sec = divmod(block_sec, 60)
        block_hr, block_min = divmod(block_min, 60)
        s1 = "Summe Blockzeit: "
        s2 = "{:02.0f}:{:02.0f}".format(block_hr, block_min)
        night_min, night_sec = divmod(night_sec, 60)
        night_hr, night_min = divmod(night_min, 60)
        s3 = "   night: "
        s4 = "{:02.0f}:{:02.0f}".format(night_hr, night_min)
        ifr_min, ifr_sec = divmod(ifr_sec, 60)
        ifr_hr, ifr_min = divmod(ifr_min, 60)
        s5 = "   IFR: "
        s6 = "{:02.0f}:{:02.0f}".format(ifr_hr, ifr_min)
        self.poutput(
            col.Fore.GREEN
            + s1
            + col.Style.RESET_ALL
            + s2
            + col.Fore.GREEN
            + s3
            + col.Style.RESET_ALL
            + s4
            + col.Fore.GREEN
            + s5
            + col.Style.RESET_ALL
            + s6
        )

        flight_min, flight_sec = divmod(flight_sec, 60)
        flight_hr, flight_min = divmod(flight_min, 60)
        s1 = "Summe Flugzeit: "
        s2 = "{:02.0f}:{:02.0f}".format(flight_hr, flight_min)
        self.poutput(col.Fore.GREEN + s1 + col.Style.RESET_ALL + s2)

        s1 = "Landings: "
        s2 = "{:>4d}".format(ldg_day + ldg_night)
        s3 = "  day: "
        s4 = "{:>4d}".format(ldg_day)
        s5 = "  night: "
        s6 = "{:>4d}".format(ldg_night)
        self.poutput(
            col.Fore.GREEN
            + s1
            + col.Style.RESET_ALL
            + s2
            + col.Fore.GREEN
            + s3
            + col.Style.RESET_ALL
            + s4
            + col.Fore.GREEN
            + s5
            + col.Style.RESET_ALL
            + s6
        )

        self.poutput()

    # parser for stat command
    parser_stat = argparse.ArgumentParser()
    parser_stat.add_argument(
        "-l", "--long", action="store_true", dest="long",
        help="show more information"
    )

    @cmd2.with_argparser(parser_stat)
    def do_stat(self, args):
        """Shows some information about currency and validity of licenses.
        Runs at startup.
        """

        today = dt.datetime.today()

        def calc_sums():
            secs = 0
            ldgs_ = 0
            for result in cur:
                diff = dt.datetime.strptime(
                    result["onblock"], "%H:%M"
                ) - dt.datetime.strptime(result["offblock"], "%H:%M")
                if diff.total_seconds() >= 0:
                    secs += diff.total_seconds()
                else:
                    secs += diff.total_seconds() + 86400  # add 24h = 86400 s

                # secs += diff.total_seconds()
                ldgs_ += int(result["landingsDay+landingsNight"])

            mins_, secs = divmod(secs, 60)
            hrs_, mins_ = divmod(mins_, 60)
            return hrs_, mins_, ldgs_

        def calc_pic_wo_pic():
            # sums for 90 days
            start_date = today + relativedelta(days=-90)
            cur.execute(
                "select offblock, onblock, "
                "landingsDay+landingsNight from flights "
                "where flightdate >= ? and  flightdate <= ?"
                "  and pilotFunction = ?",
                (start_date.strftime("%Y-%m-%d"),
                 today.strftime("%Y-%m-%d"), "PIC"),
            )

            hrs, mins, ldgs = calc_sums()
            s1 = f"  {ldgs:>3}     {int(hrs):>02d}:{int(mins):>02d} "

            # sums for 6 months
            start_date = today + relativedelta(months=-6)
            cur.execute(
                "select offblock, onblock, "
                "landingsDay+landingsNight from flights "
                "where flightdate >= ? and  flightdate <= ?"
                "  and pilotFunction = ?",
                (start_date.strftime("%Y-%m-%d"),
                 today.strftime("%Y-%m-%d"), "PIC"),
            )

            hrs, mins, ldgs = calc_sums()
            s2 = f"  {ldgs:>3}     {int(hrs):>02d}:{int(mins):>02d} "

            # sums for current year
            start_date = today.replace(month=1, day=1)
            cur.execute(
                "select offblock, onblock, "
                "landingsDay+landingsNight from flights "
                "where flightdate >= ? and  flightdate <= ?"
                "  and pilotFunction = ?",
                (start_date.strftime("%Y-%m-%d"),
                 today.strftime("%Y-%m-%d"), "PIC"),
            )

            hrs, mins, ldgs = calc_sums()
            s3 = f"  {ldgs:>3}     {int(hrs):>02d}:{int(mins):>02d} "

            # sums for one year
            start_date = today + relativedelta(years=-1)
            cur.execute(
                "select offblock, onblock, "
                "landingsDay+landingsNight from flights "
                "where flightdate >= ? and  flightdate <= ?"
                "  and pilotFunction = ?",
                (start_date.strftime("%Y-%m-%d"),
                 today.strftime("%Y-%m-%d"), "PIC"),
            )

            hrs, mins, ldgs = calc_sums()
            s4 = f"  {ldgs:>3}     {int(hrs):>02d}:{int(mins):>02d} "

            self.poutput(
                col.Fore.GREEN
                + f"{'PIC (without FI)':18}"
                + col.Style.RESET_ALL
                + s1
                + "  "
                + s2
                + "  "
                + s3
                + "  "
                + s4
            )

        def calc_fi():
            # sums for 90 days
            start_date = today + relativedelta(days=-90)
            cur.execute(
                "select offblock, onblock, "
                "landingsDay+landingsNight from flights "
                "where flightdate >= ? and  flightdate <= ?"
                "  and pilotFunction = ?",
                (start_date.strftime("%Y-%m-%d"),
                 today.strftime("%Y-%m-%d"), "FI"),
            )

            hrs, mins, ldgs = calc_sums()
            s1 = f"  {ldgs:>3}     {int(hrs):>02d}:{int(mins):>02d} "

            # sums for 6 months
            start_date = today + relativedelta(months=-6)
            cur.execute(
                "select offblock, onblock, "
                "landingsDay+landingsNight from flights "
                "where flightdate >= ? and  flightdate <= ?"
                "  and pilotFunction = ?",
                (start_date.strftime("%Y-%m-%d"),
                 today.strftime("%Y-%m-%d"), "FI"),
            )

            hrs, mins, ldgs = calc_sums()
            s2 = f"  {ldgs:>3}     {int(hrs):>02d}:{int(mins):>02d} "

            # sums for current year
            start_date = today.replace(month=1, day=1)
            cur.execute(
                "select offblock, onblock, "
                "landingsDay+landingsNight from flights "
                "where flightdate >= ? and  flightdate <= ?"
                "  and pilotFunction = ?",
                (start_date.strftime("%Y-%m-%d"),
                 today.strftime("%Y-%m-%d"), "FI"),
            )

            hrs, mins, ldgs = calc_sums()
            s3 = f"  {ldgs:>3}     {int(hrs):>02d}:{int(mins):>02d} "

            # sums for one year
            start_date = today + relativedelta(years=-1)
            cur.execute(
                "select offblock, onblock, "
                "landingsDay+landingsNight from flights "
                "where flightdate >= ? and  flightdate <= ?"
                "  and pilotFunction = ?",
                (start_date.strftime("%Y-%m-%d"),
                 today.strftime("%Y-%m-%d"), "FI"),
            )

            hrs, mins, ldgs = calc_sums()
            s4 = f"  {ldgs:>3}     {int(hrs):>02d}:{int(mins):>02d} "

            self.poutput(
                col.Fore.GREEN
                + f"{'FI':18}"
                + col.Style.RESET_ALL
                + s1
                + "  "
                + s2
                + "  "
                + s3
                + "  "
                + s4
            )

        def calc_fi_incl_pic():
            # sums for 90 days
            start_date = today + relativedelta(days=-90)
            cur.execute(
                "select offblock, onblock, "
                "landingsDay+landingsNight from flights "
                "where flightdate >= ? and  flightdate <= ?"
                "  and (pilotFunction = ? or pilotFunction = ?)",
                (
                    start_date.strftime("%Y-%m-%d"),
                    today.strftime("%Y-%m-%d"),
                    "PIC",
                    "FI",
                ),
            )

            hrs, mins, ldgs = calc_sums()
            s1 = f"  {ldgs:>3}     {int(hrs):>02d}:{int(mins):>02d} "

            # sums for 6 months
            start_date = today + relativedelta(months=-6)
            cur.execute(
                "select offblock, onblock, "
                "landingsDay+landingsNight from flights "
                "where flightdate >= ? and  flightdate <= ?"
                "  and (pilotFunction = ? or pilotFunction = ?)",
                (
                    start_date.strftime("%Y-%m-%d"),
                    today.strftime("%Y-%m-%d"),
                    "PIC",
                    "FI",
                ),
            )

            hrs, mins, ldgs = calc_sums()
            s2 = f"  {ldgs:>3}     {int(hrs):>02d}:{int(mins):>02d} "

            # sums for current year
            start_date = today.replace(month=1, day=1)
            cur.execute(
                "select offblock, onblock, "
                "landingsDay+landingsNight from flights "
                "where flightdate >= ? and  flightdate <= ?"
                "  and (pilotFunction = ? or pilotFunction = ?)",
                (
                    start_date.strftime("%Y-%m-%d"),
                    today.strftime("%Y-%m-%d"),
                    "PIC",
                    "FI",
                ),
            )

            hrs, mins, ldgs = calc_sums()
            s3 = f"  {ldgs:>3}     {int(hrs):>02d}:{int(mins):>02d} "

            # sums for one year
            start_date = today + relativedelta(years=-1)
            cur.execute(
                "select offblock, onblock, "
                "landingsDay+landingsNight from flights "
                "where flightdate >= ? and  flightdate <= ?"
                "  and (pilotFunction = ? or pilotFunction = ?)",
                (
                    start_date.strftime("%Y-%m-%d"),
                    today.strftime("%Y-%m-%d"),
                    "PIC",
                    "FI",
                ),
            )

            hrs, mins, ldgs = calc_sums()
            s4 = f"  {ldgs:>3}     {int(hrs):>02d}:{int(mins):>02d} "

            self.poutput(
                col.Fore.GREEN
                + f"{'PIC (incl. FI)':18}"
                + col.Style.RESET_ALL
                + s1
                + "  "
                + s2
                + "  "
                + s3
                + "  "
                + s4
            )

        def calc_dual():
            # sums for 90 days
            start_date = today + relativedelta(days=-90)
            cur.execute(
                "select offblock, onblock, "
                "landingsDay+landingsNight from flights "
                "where flightdate >= ? and  flightdate <= ?"
                "  and pilotFunction = ?",
                (start_date.strftime("%Y-%m-%d"),
                 today.strftime("%Y-%m-%d"), "Dual"),
            )

            hrs, mins, ldgs = calc_sums()
            s1 = f"  {ldgs:>3}     {int(hrs):>02d}:{int(mins):>02d} "

            # sums for 6 months
            start_date = today + relativedelta(months=-6)
            cur.execute(
                "select offblock, onblock, "
                "landingsDay+landingsNight from flights "
                "where flightdate >= ? and  flightdate <= ?"
                "  and pilotFunction = ?",
                (start_date.strftime("%Y-%m-%d"),
                 today.strftime("%Y-%m-%d"), "Dual"),
            )

            hrs, mins, ldgs = calc_sums()
            s2 = f"  {ldgs:>3}     {int(hrs):>02d}:{int(mins):>02d} "

            # sums for current year
            start_date = today.replace(month=1, day=1)
            cur.execute(
                "select offblock, onblock, "
                "landingsDay+landingsNight from flights "
                "where flightdate >= ? and  flightdate <= ?"
                "  and pilotFunction = ?",
                (start_date.strftime("%Y-%m-%d"),
                 today.strftime("%Y-%m-%d"), "Dual"),
            )

            hrs, mins, ldgs = calc_sums()
            s3 = f"  {ldgs:>3}     {int(hrs):>02d}:{int(mins):>02d} "

            # sums for one year
            start_date = today + relativedelta(years=-1)
            cur.execute(
                "select offblock, onblock, "
                "landingsDay+landingsNight from flights "
                "where flightdate >= ? and  flightdate <= ?"
                "  and pilotFunction = ?",
                (start_date.strftime("%Y-%m-%d"),
                 today.strftime("%Y-%m-%d"), "Dual"),
            )

            hrs, mins, ldgs = calc_sums()
            s4 = f"  {ldgs:>3}     {int(hrs):>02d}:{int(mins):>02d} "

            self.poutput(
                col.Fore.GREEN
                + f"{'Dual':18}"
                + col.Style.RESET_ALL
                + s1
                + "  "
                + s2
                + "  "
                + s3
                + "  "
                + s4
            )

        def calc_all():
            # sums for 90 days
            start_date = today + relativedelta(days=-90)
            cur.execute(
                "select offblock, onblock, "
                "landingsDay+landingsNight from flights "
                "where flightdate >= ? and  flightdate <= ?",
                (start_date.strftime("%Y-%m-%d"),
                 today.strftime("%Y-%m-%d")),
            )

            hrs, mins, ldgs = calc_sums()
            s1 = f"  {ldgs:>3}     {int(hrs):>02d}:{int(mins):>02d} "

            # sums for 6 months
            start_date = today + relativedelta(months=-6)
            cur.execute(
                "select offblock, onblock, "
                "landingsDay+landingsNight from flights "
                "where flightdate >= ? and  flightdate <= ?",
                (start_date.strftime("%Y-%m-%d"),
                 today.strftime("%Y-%m-%d")),
            )

            hrs, mins, ldgs = calc_sums()
            s2 = f"  {ldgs:>3}     {int(hrs):>02d}:{int(mins):>02d} "

            # sums for current year
            start_date = today.replace(month=1, day=1)
            cur.execute(
                "select offblock, onblock, "
                "landingsDay+landingsNight from flights "
                "where flightdate >= ? and  flightdate <= ?",
                (start_date.strftime("%Y-%m-%d"),
                 today.strftime("%Y-%m-%d")),
            )

            hrs, mins, ldgs = calc_sums()
            s3 = f"  {ldgs:>3}     {int(hrs):>02d}:{int(mins):>02d} "

            # sums for one year
            start_date = today + relativedelta(years=-1)
            cur.execute(
                "select offblock, onblock, "
                "landingsDay+landingsNight from flights "
                "where flightdate >= ? and  flightdate <= ?",
                (start_date.strftime("%Y-%m-%d"),
                 today.strftime("%Y-%m-%d")),
            )

            hrs, mins, ldgs = calc_sums()
            s4 = f"  {ldgs:>3}     {int(hrs):>02d}:{int(mins):>02d} "

            self.poutput(
                col.Fore.GREEN
                + f"{'All':18}"
                + col.Style.RESET_ALL
                + s1
                + "  "
                + s2
                + "  "
                + s3
                + "  "
                + s4
            )

        # Headers
        self.poutput(
            col.Fore.GREEN + f"{'':18}{'90 days':^16}  {'6 months':^16}  "
            f"{today.strftime('%Y'):^16}  {'1 year':^16}" + col.Style.RESET_ALL
        )
        self.poutput(
            col.Fore.GREEN
            + f"{'':18}{'Flights':^8}{'Time':^8}  {'Flights':^8}{'Time':^8}  "
            f"{'Flights':^8}{'Time':^8}  {'Flights':^8}{'Time':^8}"
            + col.Style.RESET_ALL
        )

        cur = con.cursor()

        # sums for PIC (without FI)
        calc_pic_wo_pic()

        # sums for FI
        calc_fi()

        # sums for PIC (incl. FI)
        calc_fi_incl_pic()

        if args.long:
            calc_dual()
            calc_all()

        self.poutput()

    # parser for check command
    parser_check = argparse.ArgumentParser()
    parser_check.add_argument(
        "date", nargs="?", help="date as dd.mm.yyyy, default is today"
    )
    parser_check.add_argument(
        "--hide-valid",
        dest="hide_valid",
        action="store_true",
        help="show only warnings and expired items",
    )

    @cmd2.with_argparser(parser_check)
    def do_check(self, args):
        """Checks licenses, ratings etc."""

        def check_ninety_day(_date, _cur, _class):
            # start checking from yesterday and then move forward day after day
            d = dt.datetime.today().replace(hour=0, minute=0,
                                            second=0, microsecond=0)
            d += relativedelta(days=-1)

            while True:
                ldg = 0
                datestring = (d + relativedelta(days=-90)).strftime("%Y-%m-%d")
                _cur.execute(
                    "select sum(landingsDay+landingsNight) from "
                    "flights where flightdate >= ? and "
                    "flightTimeClass = ?",
                    (datestring, _class),
                )
                row = cur.fetchone()
                if row[0] is not None:
                    ldg = int(row[0])
                if ldg < 3:
                    d += relativedelta(days=-1)  # return to the last valid day
                    break
                d += relativedelta(days=1)

            if _date <= d:
                if _date >= d + relativedelta(days=-10):
                    ret = "warning"
                else:
                    ret = "valid"
            else:
                ret = "expired"

            return ret, d

        def check_date(_date, exp_date, warning_period):
            ret = "valid"
            de = dt.datetime.strptime(exp_date, "%Y-%m-%d")
            dw = de
            if warning_period[0] == "m":
                dw += relativedelta(months=-int(warning_period[1:]))
            if warning_period[0] == "d":
                dw += relativedelta(days=-int(warning_period[1:]))
            if _date > de:
                ret = "expired"
            else:
                if _date >= dw:
                    ret = "warning"
            return ret

        date = parse_dateparam(self, args.date)

        # get all class ratings, expiration dates and warning periods
        cur = con.cursor()
        cur.execute(
            "select title, expirationDate, warningPeriod "
            "from ratings where type='CR'"
        )

        res = cur.fetchall()
        rating_list = []
        for result in res:
            rating_list.append(
                {
                    "title": result["title"],
                    "expirationDate": result["expirationDate"],
                    "warningPeriod": result["warningPeriod"],
                }
            )

        # check validity of class ratings
        for rating in rating_list:
            s1 = ""
            check_result = check_date(
                date, rating["expirationDate"], rating["warningPeriod"]
            )
            s2 = "  " + dt.datetime.strptime(
                rating["expirationDate"], "%Y-%m-%d"
            ).date().strftime("%d.%m.%Y")
            if check_result == "valid":
                s1 = (
                    col.Fore.LIGHTBLUE_EX
                    + "{:>10}".format("valid")
                    + s2
                    + col.Style.RESET_ALL
                )
            if check_result == "expired":
                s1 = (
                    col.Fore.LIGHTRED_EX
                    + "{:>10}".format("expired")
                    + s2
                    + col.Style.RESET_ALL
                )
            if check_result == "warning":
                s1 = (
                    col.Fore.LIGHTYELLOW_EX
                    + "{:>10}".format("warning")
                    + s2
                    + col.Style.RESET_ALL
                )

            if (not args.hide_valid) or check_result != "valid":
                self.poutput(
                    col.Fore.GREEN
                    + f"{'Class Rating ' + rating['title']:>20}: "
                    + col.Style.RESET_ALL
                    + s1
                )

        # check 90 day rule for class ratings
        for rating in rating_list:
            s1 = ""
            check_result, expiration_date = check_ninety_day(date,
                                                             cur,
                                                             rating["title"])
            s2 = "  " + expiration_date.strftime("%d.%m.%Y")
            if check_result == "valid":
                s1 = (
                    col.Fore.LIGHTBLUE_EX
                    + "{:>10}".format("valid")
                    + s2
                    + col.Style.RESET_ALL
                )
            if check_result == "expired":
                s1 = (
                    col.Fore.LIGHTRED_EX
                    + "{:>10}".format("expired")
                    + s2
                    + col.Style.RESET_ALL
                )
            if check_result == "warning":
                s1 = (
                    col.Fore.LIGHTYELLOW_EX
                    + "{:>10}".format("warning")
                    + s2
                    + col.Style.RESET_ALL
                )

            if (not args.hide_valid) or check_result != "valid":
                self.poutput(
                    col.Fore.GREEN
                    + f"{'90 day rule on ' + rating['title']:>20}: "
                    + col.Style.RESET_ALL
                    + s1
                )

        # check 90 day rule for spl
        s1 = ""
        check_result, expiration_date = check_ninety_day(date, cur, "UL")
        s2 = "  " + expiration_date.strftime("%d.%m.%Y")
        if check_result == "valid":
            s1 = (
                col.Fore.LIGHTBLUE_EX
                + "{:>10}".format("valid")
                + s2
                + col.Style.RESET_ALL
            )
        if check_result == "expired":
            s1 = (
                col.Fore.LIGHTRED_EX
                + "{:>10}".format("expired")
                + s2
                + col.Style.RESET_ALL
            )
        if check_result == "warning":
            s1 = (
                col.Fore.LIGHTYELLOW_EX
                + "{:>10}".format("warning")
                + s2
                + col.Style.RESET_ALL
            )

        if (not args.hide_valid) or check_result != "valid":
            self.poutput(
                col.Fore.GREEN
                + f"{'90 day rule on ' + 'UL':>20}: "
                + col.Style.RESET_ALL
                + s1
            )

        # get other ratings
        cur.execute(
            "select title, expirationDate, "
            "warningPeriod from ratings where type='OR'"
        )

        res = cur.fetchall()
        rating_list = []
        for result in res:
            rating_list.append(
                {
                    "title": result["title"],
                    "expirationDate": result["expirationDate"],
                    "warningPeriod": result["warningPeriod"],
                }
            )
        # check validity of other ratings
        for rating in rating_list:
            s1 = ""
            check_result = check_date(
                date, rating["expirationDate"], rating["warningPeriod"]
            )
            s2 = "  " + dt.datetime.strptime(
                rating["expirationDate"], "%Y-%m-%d"
            ).date().strftime("%d.%m.%Y")
            if check_result == "valid":
                s1 = (
                    col.Fore.LIGHTBLUE_EX
                    + "{:>10}".format("valid")
                    + s2
                    + col.Style.RESET_ALL
                )
            if check_result == "expired":
                s1 = (
                    col.Fore.LIGHTRED_EX
                    + "{:>10}".format("expired")
                    + s2
                    + col.Style.RESET_ALL
                )
            if check_result == "warning":
                s1 = (
                    col.Fore.LIGHTYELLOW_EX
                    + "{:>10}".format("warning")
                    + s2
                    + col.Style.RESET_ALL
                )

            if (not args.hide_valid) or check_result != "valid":
                self.poutput(
                    col.Fore.GREEN
                    + f"{rating['title']:>20}: "
                    + col.Style.RESET_ALL
                    + s1
                )

        # get all the rest
        cur.execute(
            "select title, expirationDate, "
            "warningPeriod from ratings where type='O'"
        )

        res = cur.fetchall()
        rating_list = []
        for result in res:
            rating_list.append(
                {
                    "title": result["title"],
                    "expirationDate": result["expirationDate"],
                    "warningPeriod": result["warningPeriod"],
                }
            )
        # check validity of other ratings
        for rating in rating_list:
            s1 = ""
            check_result = check_date(
                date, rating["expirationDate"], rating["warningPeriod"]
            )
            s2 = "  " + dt.datetime.strptime(
                rating["expirationDate"], "%Y-%m-%d"
            ).date().strftime("%d.%m.%Y")
            if check_result == "valid":
                s1 = (
                    col.Fore.LIGHTBLUE_EX
                    + "{:>10}".format("valid")
                    + s2
                    + col.Style.RESET_ALL
                )
            if check_result == "expired":
                s1 = (
                    col.Fore.LIGHTRED_EX
                    + "{:>10}".format("expired")
                    + s2
                    + col.Style.RESET_ALL
                )
            if check_result == "warning":
                s1 = (
                    col.Fore.LIGHTYELLOW_EX
                    + "{:>10}".format("warning")
                    + s2
                    + col.Style.RESET_ALL
                )

            if (not args.hide_valid) or check_result != "valid":
                self.poutput(
                    col.Fore.GREEN
                    + f"{rating['title']:>20}: "
                    + col.Style.RESET_ALL
                    + s1
                )

    # parser for edit_ratings command
    parser_edit_ratings = argparse.ArgumentParser()

    # noinspection PyUnusedLocal
    @cmd2.with_argparser(parser_edit_ratings)
    def do_edit_ratings(self, args):
        """Add, change or delete ratings, licenses, conditions."""
        qt_gui.execute_edit_ratings()

    # parser for edit_settings command
    parser_edit_settings = argparse.ArgumentParser()

    # noinspection PyUnusedLocal
    @cmd2.with_argparser(parser_edit_settings)
    def do_edit_settings(self, args):
        """Like it says: Edit settings."""
        qt_gui.execute_edit_settings()

    # parser for import command
    parser_import = argparse.ArgumentParser()
    parser_import.add_argument("filename", nargs=1, help="name of csv file")

    @cmd2.with_argparser(parser_import)
    def do_import(self, args):
        """Import flight from a csv file."""
        import_database(args.filename[0])

    # parser for update_airport command
    parser_update_airports = argparse.ArgumentParser()

    # noinspection PyUnusedLocal
    @cmd2.with_argparser(parser_update_airports)
    def do_update_airports(self, args):
        """Update airport database from OurAirports.com"""
        # Download csv file from OurAirports.com
        with open("airports.csv", "wb") as local_file:
            self.poutput("Download airport database.")
            response = requests.get(
                "https://ourairports.com/data/airports.csv", stream=True
            )
            total_length = response.headers.get("content-length")

            if total_length is None:  # no content length header
                local_file.write(response.content)
            else:
                dl = 0
                total_length = int(total_length)
                for data in response.iter_content(chunk_size=4096):
                    dl += len(data)
                    local_file.write(data)
                    ratio = dl / total_length
                    sys.stdout.write(
                        f"\r|{'=' * int(ratio * 50)}"
                        "{' ' * int((1 - ratio) * 50)}> {int(ratio * 100)}% "
                    )
                    sys.stdout.flush()
                sys.stdout.write("\n")

        cur_ap = con_ap.cursor()

        # remove old airport entries
        cur_ap.execute("delete from airports")

        # write airports to database
        with open("airports.csv", "r") as local_file:
            csv_reader = csv.reader(local_file, delimiter=",")
            next(csv_reader)  # skip first for it contains headers
            for row in csv_reader:
                cur_ap.execute(
                    "insert into airports (icaoId, name,"
                    " lat, long, elev) values "
                    "(?, ?, ?, ?, ?)",
                    (row[1], row[3], row[4], row[5], row[6]),
                )
            con_ap.commit()

    # parser for search_airport command
    parser_search_airport = argparse.ArgumentParser()
    parser_search_airport.add_argument(
        "search_string", nargs=1, help="Name or identifier or part of those"
    )
    parser_search_airport.add_argument(
        "-id", action="store_true", help="Search identifiers only"
    )

    @cmd2.with_argparser(parser_search_airport)
    def do_search_airports(self, args):
        """Search airport by identifier or name."""
        cur = con_ap.cursor()
        if not args.id:
            cur.execute(
                "select * from airports where name like ? or icaoId like ?",
                ("%" + args.search_string[0] + "%", "%" +
                 args.search_string[0] + "%"),
            )
        else:
            cur.execute(
                "select * from airports where icaoId like ?",
                ("%" + args.search_string[0] + "%",),
            )

        for result in cur:
            self.poutput(f'{result["icaoID"]:>8} {result["name"]}')


def main():
    # start cmd2 command loop
    CmdApp().cmdloop()

    # close db connections
    con.close()
    con_ap.close()


if __name__ == "__main__":
    # Determine database name from command line argument
    if len(sys.argv) < 2:
        print("usage: flightlog [filename]")
        sys.exit(1)
    db_name = sys.argv[1]
    del sys.argv[1:]

    # create database connection
    con = create_connection(db_name)
    con.row_factory = sq.Row

    # create airport database connection
    # TODO good location for airports.db file?
    con_ap = create_connection("airports.db")
    con_ap.row_factory = sq.Row

    # check if all tables exists and create them if necessary
    create_tables()

    # Prepare Qt Gui
    qt_gui = QtGui(db_name)

    main()
