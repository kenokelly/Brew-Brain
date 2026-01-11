import sys
import os
from unittest.mock import MagicMock, patch

# Add app to path
sys.path.append(os.getcwd())

# Mock configuration
with patch('app.services.sourcing.get_config') as mock_config:
    mock_config.return_value = "fake_api_key"
    
    # Import SUT
    from app.services import sourcing

    def test_integration():
        print("Testing compare_recipe_prices with mocked SerpApi...")
        
        # Test Data
        recipe = {
            "hops": [{"name": "Citra", "amount": 100}],
            "fermentables": [],
            "yeasts": []
        }
        
        # Mock SerpApi Response
        mock_results_tmm = {
            "organic_results": [
                {
                    "title": "Citra Hops - The Malt Miller",
                    "link": "https://themaltmiller.co.uk/citra",
                    "snippet": "Buy Citra Hops 100g. Price: £7.50. Tropical fruit flavors.",
                    "rich_snippet": {
                        "top": {
                            "detected_extensions": {
                                "price": "7.50"
                            }
                        }
                    }
                }
            ]
        }
        
        mock_results_geb = {
            "organic_results": [
                {
                    "title": "Citra Hops - Get Er Brewed",
                    "link": "https://geterbrewed.com/citra",
                    "snippet": "Citra Hops 2023 100g 8.00 GBP. Best hops.",
                    # No rich snippet here, testing fallback
                }
            ]
        }
        
        # Setup Mock
        with patch('app.services.sourcing.GoogleSearch') as MockSearch:
            # We need to return different results based on the query
            def side_effect(params):
                query = params['q']
                mock_instance = MagicMock()
                
                if "themaltmiller" in query:
                    mock_instance.get_dict.return_value = mock_results_tmm
                elif "geterbrewed" in query:
                    mock_instance.get_dict.return_value = mock_results_geb
                else:
                    mock_instance.get_dict.return_value = {"organic_results": []}
                    
                return mock_instance

            MockSearch.side_effect = side_effect
            
            # Run Code
            result = sourcing.compare_recipe_prices(recipe)
            
            print("Result Breakdown:")
            for row in result['breakdown']:
                print(f"Item: {row['name']}")
                print(f"  TMM Price: {row['tmm_price']}")
                print(f"  GEB Price: {row['geb_price']}")
                print(f"  Best Vendor: {row['best_vendor']}")
                
            print("-" * 20)
            print(f"Total TMM: {result['total_tmm']}")
            print(f"Total GEB: {result['total_geb']}")
            
            # Assertions
            tmm = result['breakdown'][0]['tmm_price']
            geb = result['breakdown'][0]['geb_price']
            
            if tmm == 7.5: print("✅ TMM Price Correct (Rich Snippet)")
            else: print(f"❌ TMM Price Failed: Got {tmm}")
            
            if geb == 8.0: print("✅ GEB Price Correct (Regex Fallback)")
            else: print(f"❌ GEB Price Failed: Got {geb}")

    if __name__ == "__main__":
        try:
            test_integration()
        except Exception as e:
            print(f"Test Failed: {e}")
            import traceback
            traceback.print_exc()
