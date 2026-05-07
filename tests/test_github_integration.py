import unittest
from unittest.mock import patch, MagicMock
import sys

# Mock missing dependencies
sys.modules['github'] = MagicMock()

influxdb_client_mock = MagicMock()
influxdb_client_mock.client.write_api.SYNCHRONOUS = "synchronous"
sys.modules['influxdb_client'] = influxdb_client_mock
sys.modules['influxdb_client.client'] = influxdb_client_mock.client
sys.modules['influxdb_client.client.write_api'] = influxdb_client_mock.client.write_api

from services.github_integration import push_recipe_to_repo

class TestGithubIntegration(unittest.TestCase):
    @patch('services.github_integration.Github')
    def test_push_recipe_to_repo_update_existing(self, mock_github):
        mock_g = MagicMock()
        mock_github.return_value = mock_g
        mock_repo = MagicMock()
        mock_g.get_repo.return_value = mock_repo

        mock_contents = MagicMock()
        mock_contents.path = "recipes/Test_Recipe.xml"
        mock_contents.sha = "123456"
        mock_repo.get_contents.return_value = mock_contents

        recipe_data = {"name": "Test Recipe", "xml_content": "<xml/>"}

        result = push_recipe_to_repo(recipe_data, "fake_token", "fake_repo")

        self.assertEqual(result.get("status"), "success")
        self.assertEqual(result.get("message"), "Updated recipes/Test_Recipe.xml in fake_repo")
        mock_repo.update_file.assert_called_once_with("recipes/Test_Recipe.xml", "Update recipe Test_Recipe", "<xml/>", "123456")
        mock_repo.create_file.assert_not_called()

    @patch('services.github_integration.Github')
    def test_push_recipe_to_repo_create_new(self, mock_github):
        mock_g = MagicMock()
        mock_github.return_value = mock_g
        mock_repo = MagicMock()
        mock_g.get_repo.return_value = mock_repo

        mock_repo.get_contents.side_effect = Exception("Not Found")

        recipe_data = {"name": "Test Recipe", "xml_content": "<xml/>"}

        result = push_recipe_to_repo(recipe_data, "fake_token", "fake_repo")

        self.assertEqual(result.get("status"), "success")
        self.assertEqual(result.get("message"), "Created recipes/Test_Recipe.xml in fake_repo")
        mock_repo.create_file.assert_called_once_with("recipes/Test_Recipe.xml", "Add recipe Test_Recipe", "<xml/>")
        mock_repo.update_file.assert_not_called()

    @patch('services.github_integration.Github')
    def test_push_recipe_to_repo_global_error(self, mock_github):
        mock_github.side_effect = Exception("Auth error")

        recipe_data = {"name": "Test Recipe", "xml_content": "<xml/>"}

        result = push_recipe_to_repo(recipe_data, "fake_token", "fake_repo")

        self.assertEqual(result.get("error"), "Auth error")

    @patch('services.github_integration.Github')
    def test_push_recipe_to_repo_no_xml_provided(self, mock_github):
        recipe_data = {"name": "Test Recipe", "source_url": "http://example.com/recipe.xml"}

        result = push_recipe_to_repo(recipe_data, "fake_token", "fake_repo")
        self.assertEqual(result.get("error"), "No XML content provided to save.")

    @patch('services.github_integration.Github')
    def test_push_recipe_to_repo_fallback_xml(self, mock_github):
        mock_g = MagicMock()
        mock_github.return_value = mock_g
        mock_repo = MagicMock()
        mock_g.get_repo.return_value = mock_repo

        mock_repo.get_contents.side_effect = Exception("Not Found")

        recipe_data = {"name": "Fallback Recipe", "og": 1.050, "ibu": 40, "abv": 5.0, "source_url": "http://example.com/no-xml"}

        result = push_recipe_to_repo(recipe_data, "fake_token", "fake_repo")

        self.assertEqual(result.get("status"), "success")
        self.assertEqual(result.get("message"), "Created recipes/Fallback_Recipe.xml in fake_repo")
        mock_repo.create_file.assert_called_once()
        args, kwargs = mock_repo.create_file.call_args
        self.assertEqual(args[0], "recipes/Fallback_Recipe.xml")
        self.assertIn("Fallback Recipe", args[2])
        self.assertIn("1.05", args[2])
        self.assertIn("40", args[2])

if __name__ == '__main__':
    unittest.main()
