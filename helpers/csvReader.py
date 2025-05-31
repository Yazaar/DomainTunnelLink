from pathlib import Path
import csv

class CSVReader:
  def __init__(self, file: Path):
    self.headers: list[str] = []
    self.rows: list[list[str]] = []
    self.data: list[dict[str, str]] = []

    if not file.exists():
      return

    rawData: list[list[str]] = []
    with open(file, 'r') as f:
      reader = csv.reader(f)
      rawData = [i for i in reader]

    self.headers = rawData[0]
    self.rows = rawData[1:]

    if len(self.rows) == 0: return

    rowLen = len(self.headers)
    iterator = list(range(rowLen))

    for row in self.rows:
      if len(row) == rowLen:
        dataRow = {}
        for i in iterator:
          dataRow[self.headers[i]] = row[i]
        self.data.append(dataRow)
