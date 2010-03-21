PRAGMA default_cache_size = 2000000;

ALTER TABLE MachineInfo RENAME TO MachineInfoOld;
CREATE TABLE MachineInfo
       (ID             INTEGER PRIMARY KEY,
        Machine        INTEGER,
        Key            TEXT,
        Value          TEXT,
        FOREIGN KEY(Machine) REFERENCES Machine(ID));
INSERT INTO MachineInfo (Machine,Key,Value)
  SELECT Machine,Key,Value FROM MachineInfoOld;
DROP TABLE MachineInfoOld;

ALTER TABLE RunInfo RENAME TO RunInfoOld;
CREATE TABLE RunInfo
       (ID             INTEGER PRIMARY KEY,
        Run            INTEGER,
        Key            TEXT,
        Value          TEXT,
        FOREIGN KEY(Run) REFERENCES Run(ID));
INSERT INTO RunInfo (Run,Key,Value)
  SELECT Run,Key,Value FROM RunInfoOld;
DROP TABLE RunInfoOld;

ALTER TABLE TestInfo RENAME TO TestInfoOld;
CREATE TABLE TestInfo
       (ID             INTEGER PRIMARY KEY,
        Test           INTEGER,
        Key            TEXT,
        Value          TEXT,
        FOREIGN KEY(Test) REFERENCES Test(ID));
INSERT INTO TestInfo (Test,Key,Value)
  SELECT Test,Key,Value FROM TestInfoOld;
DROP TABLE TestInfoOld;

ALTER TABLE Sample RENAME TO SampleOld;
CREATE TABLE Sample
       (ID              INTEGER PRIMARY KEY,
        RunID           INTEGER,
        TestID          INTEGER,
        Key             TEXT,
        Value           REAL,
        FOREIGN KEY(RunID) REFERENCES Run(ID),
        FOREIGN KEY(TestID) REFERENCES Test(ID));
DROP INDEX [Sample_IDX1];
DROP INDEX [Sample_IDX2];
BEGIN TRANSACTION;
INSERT INTO Sample (RunID,TestID,Key,Value)
  SELECT RunID,TestID,Key,Value FROM SampleOld;
COMMIT TRANSACTION;
BEGIN TRANSACTION; CREATE INDEX [Sample_IDX1] ON Sample(RunID); COMMIT TRANSACTION;
BEGIN TRANSACTION; CREATE INDEX [Sample_IDX2] ON Sample(TestID); COMMIT TRANSACTION;
DROP TABLE SampleOld;
