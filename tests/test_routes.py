import unittest
from flask import json
from src.app import app
from src.config import Config
from src.core.models import DataProcessor, LandUseAnalyzer
from unittest.mock import patch

class TestLandUseRoutes(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

        # Mock data for testing
        self.mock_landuse_data = {
            '110101': {
                1980: {'耕地': 100.0, '建设用地': 50.0},
                2000: {'耕地': 80.0, '建设用地': 70.0},
                2020: {'耕地': 60.0, '建设用地': 90.0}
            }
        }

        # Patch app.config to inject mock data and components
        with app.app_context():
            app.config['data_processor'] = DataProcessor()
            app.config['land_use_analyzer'] = LandUseAnalyzer()
            app.config['landuse_data'] = self.mock_landuse_data

    def test_get_landuse_data_success(self):
        response = self.app.get('/api/landuse?county_id=110101&year=1980')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['county_id'], '110101')
        self.assertEqual(data['year'], 1980)
        self.assertIn('耕地', data['landuse_data'])

    def test_get_landuse_data_missing_county_id(self):
        response = self.app.get('/api/landuse?year=1980')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Missing county_id parameter", data['details'])

    def test_get_landuse_data_missing_year(self):
        response = self.app.get('/api/landuse?county_id=110101')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Missing year parameter", data['details'])

    def test_get_landuse_dat-invalid_year(self):
        response = self.app.get('/api/landuse?county_id=110101&year=abc')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Year must be an integer", data['details'])

    def test_get_landuse_data_not_found(self):
        response = self.app.get('/api/landuse?county_id=999999&year=1980')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 404)
        self.assertIn("No data found for the specified county and year", data['details'])

    def test_get_change_indices_success(self):
        response = self.app.get('/api/change-indices?county_id=110101&start_year=1980&end_year=2000')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['county_id'], '110101')
        self.assertEqual(data['period'], '1980-2000')
        self.assertIn('耕地', data['change_indices'])

    def test_get_change_indices_missing_county_id(self):
        response = self.app.get('/api/change-indices?start_year=1980&end_year=2000')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Missing county_id parameter", data['details'])

    def test_get_change_indices_invalid_year(self):
        response = self.app.get('/api/change-indices?county_id=110101&start_year=abc&end_year=2000')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("start_year and end_year must be integers", data['details'])

    def test_get_change_indices_start_year_greater_than_end_year(self):
        response = self.app.get('/api/change-indices?county_id=110101&start_year=2000&end_year=1980')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("start_year must be less than end_year", data['details'])

    def test_get_change_indices_not_found_data(self):
        response = self.app.get('/api/change-indices?county_id=110101&start_year=1950&end_year=1960')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 404)
        self.assertIn("Not enough data to calculate indices", data['details'])

    def test_get_transition_matrix_success(self):
        response = self.app.get('/api/transition-matrix?county_id=110101&start_year=1980&end_year=2000')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['county_id'], '110101')
        self.assertEqual(data['period'], '1980-2000')
        self.assertIn('transition_matrix', data)

    def test_get_transition_matrix_missing_county_id(self):
        response = self.app.get('/api/transition-matrix?start_year=1980&end_year=2000')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Missing county_id parameter", data['details'])

    def test_get_transition_matrix_invalid_year(self):
        response = self.app.get('/api/transition-matrix?county_id=110101&start_year=abc&end_year=2000')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("start_year and end_year must be integers", data['details'])

    def test_get_transition_matrix_start_year_greater_than_end_year(self):
        response = self.app.get('/api/transition-matrix?county_id=110101&start_year=2000&end_year=1980')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("start_year must be less than end_year", data['details'])

    def test_get_transition_matrix_not_found_data(self):
        response = self.app.get('/api/transition-matrix?county_id=110101&start_year=1950&end_year=1960')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 404)
        self.assertIn("Not enough data to calculate transition matrix", data['details'])

if __name__ == '__main__':
    unittest.main()
