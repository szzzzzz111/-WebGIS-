import unittest
import pandas as pd
import math
from src.core.models import LandUseAnalyzer, DataProcessor

class TestLandUseAnalyzer(unittest.TestCase):

    def setUp(self):
        self.analyzer = LandUseAnalyzer()

    def test_land_use_dynamic_degree(self):
        # Test case 1: Positive change
        self.assertAlmostEqual(self.analyzer.land_use_dynamic_degree(100, 150, 10), 5.0)
        # Test case 2: Negative change
        self.assertAlmostEqual(self.analyzer.land_use_dynamic_degree(100, 50, 10), -5.0)
        # Test case 3: No change
        self.assertAlmostEqual(self.analyzer.land_use_dynamic_degree(100, 100, 10), 0.0)
        # Test case 4: Initial area is zero
        self.assertAlmostEqual(self.analyzer.land_use_dynamic_degree(0, 50, 10), 0.0)

    def test_land_use_change_rate(self):
        # Test case 1: Positive change
        self.assertAlmostEqual(self.analyzer.land_use_change_rate(100, 200), 100.0)
        # Test case 2: Negative change
        self.assertAlmostEqual(self.analyzer.land_use_change_rate(100, 50), -50.0)
        # Test case 3: No change
        self.assertAlmostEqual(self.analyzer.land_use_change_rate(100, 100), 0.0)
        # Test case 4: Initial area is zero
        self.assertAlmostEqual(self.analyzer.land_use_change_rate(0, 50), 0.0)

    def test_comprehensive_land_use_index(self):
        # Test case 1: Basic scenario
        areas = {'耕地': 100, '建设用地': 50}
        # Weights: 耕地: 3, 建设用地: 4
        # (100/150)*3 + (50/150)*4 = (2/3)*3 + (1/3)*4 = 2 + 4/3 = 10/3 ~ 3.3333
        self.assertAlmostEqual(self.analyzer.comprehensive_land_use_index(areas), (10/3) * 100, places=2)
        
        # Test case 2: Empty areas
        self.assertAlmostEqual(self.analyzer.comprehensive_land_use_index({}), 0.0)
        
        # Test case 3: Areas with unknown land types (should be ignored)
        areas_with_unknown = {'耕地': 100, '未知': 50}
        # (100/150)*3 = 2
        self.assertAlmostEqual(self.analyzer.comprehensive_land_use_index(areas_with_unknown), (100/150 * 3) * 100, places=2)

    def test_land_use_diversity_index(self):
        # Test case 1: Diverse areas
        areas = {'耕地': 100, '建设用地': 100, '林地': 100}
        total = 300
        p = 100/300 # 1/3
        expected = -(p * math.log(p) + p * math.log(p) + p * math.log(p))
        self.assertAlmostEqual(self.analyzer.land_use_diversity_index(areas), expected)
        
        # Test case 2: Single land type
        areas_single = {'耕地': 100}
        self.assertAlmostEqual(self.analyzer.land_use_diversity_index(areas_single), -0.0)
        
        # Test case 3: Empty areas
        self.assertAlmostEqual(self.analyzer.land_use_diversity_index({}), 0.0)

    def test_land_use_transition_matrix(self):
        start_data = {'耕地': 100, '林地': 50, '建设用地': 20}
        end_data = {'耕地': 80, '林地': 60, '建设用地': 30, '水域': 10}

        matrix = self.analyzer.land_use_transition_matrix(start_data, end_data)

        # Expected values (simplified calculation based on current implementation logic)
        # Persistence:
        # 耕地: min(100, 80) = 80
        # 林地: min(50, 60) = 50
        # 建设用地: min(20, 30) = 20
        
        # Gross Loss:
        # 耕地: 100 - 80 = 20
        # 林地: 50 - 50 = 0
        # 建设用地: 20 - 20 = 0
        
        # Gross Gain:
        # 耕地: 80 - 80 = 0
        # 林地: 60 - 50 = 10
        # 建设用地: 30 - 20 = 10
        # 水域: 10 - 0 = 10
        
        # Total Gross Gain = 10 + 10 = 20
        
        # Distribute 耕地 loss (20) to gaining types (林地, 建设用地, 水域)
        # 林地 gain ratio = 10/20 = 0.5
        # 建设用地 gain ratio = 10/20 = 0.5
        # 水域 gain ratio = 10/20 = 0.5

        # So, 耕地 -> 林地 = 20 * (10/30) = 6.6667 (if water is also a gaining type, current simplified distribution might be less precise)
        # Given the current simple proportional distribution in the implementation,
        # let's re-evaluate based on how it would specifically allocate.

        # Recalculate based on current proportional distribution logic:
        # Total gross gain for distribution:林地(10) + 建设用地(10) + 水域(10) = 30 (assuming Water also contributes to gain for distribution ratio)
        # However, the current implementation only distributes to *gaining* types defined by end_data.get(lu_type, 0.0) - transition_matrix[lu_type][lu_type] > 0 
        # In `process_raster_data`, `unique_land_use_values` is used for `land_value`, which assumes numeric representations.
        # In `land_use_transition_matrix`, string keys are used.
        # The simplified distribution needs to be carefully aligned.

        # Let's consider the simplified proportional distribution directly from the code logic for the test.
        # sum_of_gains_from_others = total_gross_gain['林地'] + total_gross_gain['建设用地'] + total_gross_gain['水域'] = 10 + 10 + 10 = 30
        # Loss from 耕地 = 20
        # 耕地 -> 林地: 20 * (10/30) = 6.6667
        # 耕地 -> 建设用地: 20 * (10/30) = 6.6667
        # 耕地 -> 水域: 20 * (10/30) = 6.6667

        # Expected matrix after distribution:
        # 耕地: {耕地: 80, 林地: 6.6667, 建设用地: 6.6667, 水域: 6.6667}
        # 林地: {耕地: 0, 林地: 50, 建设用地: 0, 水域: 0}
        # 建设用地: {耕地: 0, 林地: 0, 建设用地: 20, 水域: 0}
        # 水域: {耕地: 0, 林地: 0, 建设用地: 0, 水域: 0}
        # Note: '水域' in start_data would be 0, so it can't lose anything.

        # Re-verify the distribution logic: `total_gross_gain` is correctly calculated for existing and new types.
        # `sum_of_gains_from_others` = sum of positive `net_changes` from types that did *not* have persistence + gains from new types
        # No, `total_gross_gain` is `max(0.0, end_data.get(lu_type, 0.0) - transition_matrix[lu_type][lu_type])`
        # This means, for林地: max(0, 60-50) = 10. For 建设用地: max(0, 30-20)=10. For 水域: max(0, 10-0)=10. So sum_of_gains_from_others is 30.

        # Let's write assertions for the known persistence values first
        self.assertAlmostEqual(matrix['耕地']['耕地'], 80.0)
        self.assertAlmostEqual(matrix['林地']['林地'], 50.0)
        self.assertAlmostEqual(matrix['建设用地']['建设用地'], 20.0)

        # Test the transitions based on the simplified proportional distribution
        self.assertAlmostEqual(matrix['耕地']['林地'], 6.6667, places=3)
        self.assertAlmostEqual(matrix['耕地']['建设用地'], 6.6667, places=3)
        self.assertAlmostEqual(matrix['耕地']['水域'], 6.6667, places=3)

        # Verify that other cells are zero or very close to zero
        self.assertAlmostEqual(matrix['林地']['耕地'], 0.0)
        self.assertAlmostEqual(matrix['林地']['建设用地'], 0.0)
        self.assertAlmostEqual(matrix['林地']['水域'], 0.0)
        self.assertAlmostEqual(matrix['建设用地']['耕地'], 0.0)
        self.assertAlmostEqual(matrix['建设用地']['林地'], 0.0)
        self.assertAlmostEqual(matrix['建设用地']['水域'], 0.0)
        self.assertAlmostEqual(matrix['水域']['耕地'], 0.0)
        self.assertAlmostEqual(matrix['水域']['林地'], 0.0)
        self.assertAlmostEqual(matrix['水域']['建设用地'], 0.0)
        self.assertAlmostEqual(matrix['水域']['水域'], 0.0) # No initial area for water

class TestDataProcessor(unittest.TestCase):

    def setUp(self):
        self.processor = DataProcessor()

    # Note: load_landuse_data and process_raster_data involve file I/O and database interactions,
    # which are harder to test in isolation without mocking. We'll focus on aggregate_by_county_year
    # for now, as it's a pure function given a DataFrame.

    def test_aggregate_by_county_year(self):
        raw_data = pd.DataFrame([
            {'county_id': '110101', 'county_name': '东城区', 'year': 1980, 'land_type': '耕地', 'area': 100},
            {'county_id': '110101', 'county_name': '东城区', 'year': 1980, 'land_type': '建设用地', 'area': 50},
            {'county_id': '110101', 'county_name': '东城区', 'year': 2000, 'land_type': '耕地', 'area': 80},
            {'county_id': '110101', 'county_name': '东城区', 'year': 2000, 'land_type': '建设用地', 'area': 70},
            {'county_id': '110102', 'county_name': '西城区', 'year': 1980, 'land_type': '林地', 'area': 200},
        ])
        
        aggregated_data = self.processor.aggregate_by_county_year(raw_data)
        
        expected_data = {
            '110101': {
                1980: {'耕地': 100.0, '建设用地': 50.0},
                2000: {'耕地': 80.0, '建设用地': 70.0}
            },
            '110102': {
                1980: {'林地': 200.0}
            }
        }
        
        self.assertDictEqual(aggregated_data, expected_data)

    def test_aggregate_by_county_year_empty_data(self):
        empty_data = pd.DataFrame()
        aggregated_data = self.processor.aggregate_by_county_year(empty_data)
        self.assertDictEqual(aggregated_data, {})

    def test_calculate_area_statistics(self):
        aggregated_data = {
            '110101': {
                1980: {'耕地': 100.0, '建设用地': 50.0},
                2000: {'耕地': 80.0, '建设用地': 70.0}
            },
            '110102': {
                1980: {'林地': 200.0}
            }
        }

        statistics = self.processor.calculate_area_statistics(aggregated_data)
        
        expected_statistics = {
            '110101': {
                1980: {'total_area': 150.0},
                2000: {'total_area': 150.0}
            },
            '110102': {
                1980: {'total_area': 200.0}
            }
        }

        self.assertDictEqual(statistics, expected_statistics)

    def test_calculate_area_statistics_empty_data(self):
        statistics = self.processor.calculate_area_statistics({})
        self.assertDictEqual(statistics, {})

if __name__ == '__main__':
    unittest.main()
