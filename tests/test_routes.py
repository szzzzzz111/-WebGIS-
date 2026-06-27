import unittest
from flask import json
from src.app import app
from src.config import Config
from src.core.models import DataProcessor, LandUseAnalyzer
from src.api.routes import (
    _api_docs_payload,
    _cache_transition_matrix,
    _get_cached_transition_matrix,
    _is_tif_filename,
    _sum_landuse_by_year,
    _sum_transition_matrices,
    _transition_matrix_cache,
)
from unittest.mock import patch

class TestLandUseRoutes(unittest.TestCase):

    def setUp(self):
        _transition_matrix_cache.clear()
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

    def test_transition_matrix_cache(self):
        cache_key = ('110101', 1980, 2000)
        matrix = {'耕地': {'耕地': 80.0}}

        _cache_transition_matrix(cache_key, matrix)

        self.assertEqual(_get_cached_transition_matrix(cache_key), matrix)

    def test_sum_landuse_by_year(self):
        source = {
            '110101': {
                1980: {'耕地': 100.0, '建设用地': 50.0},
                2020: {'耕地': 80.0}
            },
            '110102': {
                1980: {'耕地': 30.0, '林地': 20.0},
                2020: {'耕地': 40.0}
            }
        }

        result = _sum_landuse_by_year(source, ['110101', '110102'])

        self.assertEqual(result['1980']['耕地'], 130.0)
        self.assertEqual(result['1980']['建设用地'], 50.0)
        self.assertEqual(result['1980']['林地'], 20.0)
        self.assertEqual(result['2020']['耕地'], 120.0)

    def test_sum_transition_matrices(self):
        matrices = [
            {'耕地': {'耕地': 80.0, '建设用地': 20.0}},
            {'耕地': {'耕地': 40.0, '建设用地': 10.0}}
        ]

        result = _sum_transition_matrices(matrices)

        self.assertEqual(result['耕地']['耕地'], 120.0)
        self.assertEqual(result['耕地']['建设用地'], 30.0)

    def test_is_tif_filename(self):
        self.assertTrue(_is_tif_filename('2025.tif'))
        self.assertTrue(_is_tif_filename('2025.TIFF'))
        self.assertFalse(_is_tif_filename('2025.png'))

    def test_api_docs_payload(self):
        docs = _api_docs_payload()

        self.assertIn('endpoints', docs)
        self.assertTrue(any(item['path'] == '/api/composite-analysis' for item in docs['endpoints']))

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

    def test_get_landuse_data_invalid_year(self):
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
