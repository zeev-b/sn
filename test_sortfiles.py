import unittest
import tempfile
import os

from sortfiles import extract_year_from_transcript


class TestExtractYearFromTranscript(unittest.TestCase):

    def create_temp_file(self, content):
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8")
        tmp.write(content)
        tmp.close()
        return tmp.name

    def test_valid_date(self):
        path = self.create_temp_file("DATE:\t\tMay 26, 2015")
        self.assertEqual(extract_year_from_transcript(path), 2015)
        os.unlink(path)

    def test_invalid_date_format(self):
        path = self.create_temp_file("DATE:\t\t2015-05-26")
        self.assertIsNone(extract_year_from_transcript(path))
        os.unlink(path)

    def test_missing_date_line(self):
        path = self.create_temp_file("No date here")
        self.assertIsNone(extract_year_from_transcript(path))
        os.unlink(path)

    def test_corrupt_date_string(self):
        path = self.create_temp_file("DATE:\t\tNot a date")
        self.assertIsNone(extract_year_from_transcript(path))
        os.unlink(path)


if __name__ == '__main__':
    unittest.main()
