from pathlib import Path
import csv
import logging

logger = logging.getLogger(__name__)

class CSVReader:
  def __init__(self, file: Path):
    self.headers: list[str] = []
    self.rows: list[list[str]] = []
    self.data: list[dict[str, str]] = []

    if not file.exists():
      return

    rawData: list[list[str]] = []
    try:
      with open(file, 'r') as f:
        reader = csv.reader(f)
        rawData = [i for i in reader]
    except Exception as e:
      logger.error(f'Failed to read CSV file {file}: {str(e)}')
      return

    if len(rawData) == 0:
      return

    self.headers = rawData[0]
    self.rows = rawData[1:]

    rowLen = len(self.headers)
    iterator = list(range(rowLen))

    for row in self.rows:
      if len(row) == rowLen:
        dataRow = {}
        for i in iterator:
          dataRow[self.headers[i]] = row[i]
        self.data.append(dataRow)
