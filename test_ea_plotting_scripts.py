import unittest
import createPlots
import treatment_list as tl
import global_options as go


class TestCreatePlots(unittest.TestCase):
    def test_example_config(self):
        createPlots.init_options()
        createPlots.execute_plots(["-c", "examples/exampleConfig.txt", "--debug", "plot", "--debug", "files"])

    def test_minimal_config(self):
        createPlots.init_options()
        createPlots.execute_plots(["-c", "examples/minimalConfig.txt", "--debug", "plot", "--debug", "files"])

    def test_four_treatments_config(self):
        createPlots.init_options()
        createPlots.execute_plots(["-c", "examples/fourTreatmentsConfig.txt",
                                   "--debug", "plot", "--debug", "files"])


class TestTreatmentList(unittest.TestCase):
    def test_hash_list_of_strings(self):
        hash1 = tl.hash_list_of_strings(["a", "b", "c"])
        hash2 = tl.hash_list_of_strings(["a", "b", "d"])
        hash3 = tl.hash_list_of_strings(["aasd", "fffb", "d"])
        hash4 = tl.hash_list_of_strings(["a", "b", "c"])
        self.assertTrue(len(hash1) == 40)
        self.assertTrue(len(hash2) == 40)
        self.assertTrue(len(hash3) == 40)
        self.assertNotEqual(hash1, hash2)
        self.assertNotEqual(hash1, hash3)
        self.assertEqual(hash1, hash4)

    def test_create_prefix(self):
        root_dir = "/Users/me/Experiments/my_experiment"
        files = ["/Users/me/Experiments/my_experiment/run_1/data.dat"]
        self.assertEqual(tl.create_prefix(root_dir, files), "run_1_data.dat")
        files.append("/Users/me/Experiments/my_experiment/run_2/data.dat")
        self.assertEqual(tl.create_prefix(root_dir, files),
                         tl.hash_list_of_strings(["run_1", "run_2"])[:16] + "_data.dat")


if __name__ == '__main__':
    unittest.main()
