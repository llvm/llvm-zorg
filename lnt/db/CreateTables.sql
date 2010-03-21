-- ===- CreateTables.sql - Create SQL Performance DB Tables -----------------===
--
--                     The LLVM Compiler Infrastructure
--
-- This file is distributed under the University of Illinois Open Source
-- License. See LICENSE.TXT for details.
--
-- ===-----------------------------------------------------------------------===

-- Machine Table
-- Main machine list.
CREATE TABLE Machine
       (ID              INTEGER PRIMARY KEY,
        Name            VARCHAR(512),
        Number          INTEGER);

CREATE INDEX [Machine_IDX1] ON Machine(ID);
CREATE INDEX [Machine_IDX2] ON Machine(Name);

-- Machine Info Table
-- Arbitrary information associated with a machine.
CREATE TABLE MachineInfo
       (ID             INTEGER PRIMARY KEY,
        Machine        INTEGER,
        `Key`          TEXT,
        Value          TEXT,
        FOREIGN KEY(Machine) REFERENCES Machine(ID));

-- Run Table
-- A specific run of a test on a machine.
CREATE TABLE Run
       (ID              INTEGER PRIMARY KEY,
        MachineID       INTEGER,
        StartTime       DATETIME,
        EndTime         DATETIME,
        FOREIGN KEY(MachineID) REFERENCES Machine(ID));

CREATE INDEX [Run_IDX1] ON Run(ID);

-- Run Info Table
-- Arbitrary information about a run.
CREATE TABLE RunInfo
       (ID             INTEGER PRIMARY KEY,
        Run            INTEGER,
        `Key`          TEXT,
        Value          TEXT,
        FOREIGN KEY(Run) REFERENCES Run(ID));

-- Test Table
-- Tests are made up of several samples.
CREATE TABLE Test
       (ID              INTEGER PRIMARY KEY,
        Name            VARCHAR(512),
        Number          INTEGER);

CREATE INDEX [Test_IDX1] ON Test(ID);
CREATE INDEX [Test_IDX2] ON Test(Name);

-- Run Info Table
-- Arbitrary information about a run.
CREATE TABLE TestInfo
       (ID             INTEGER PRIMARY KEY,
        Test           INTEGER,
        `Key`          TEXT,
        Value          TEXT,
        FOREIGN KEY(Test) REFERENCES Test(ID));

-- Sample Table
-- One data point for a particular test.
CREATE TABLE Sample
       (ID              INTEGER PRIMARY KEY,
        RunID           INTEGER,
        TestID          INTEGER,
        Value           REAL,
        FOREIGN KEY(RunID) REFERENCES Run(ID),
        FOREIGN KEY(TestID) REFERENCES Test(ID));

CREATE INDEX [Sample_IDX1] ON Sample(RunID);
CREATE INDEX [Sample_IDX2] ON Sample(TestID);
CREATE INDEX [Sample_IDX3] ON Sample(TestID, RunID);
