import simple_pygame, unittest

class TestTransform(unittest.TestCase):
    @classmethod
    def setUpClass(self) -> None:
        self.successfully_imported = simple_pygame.init((simple_pygame.TerminalModule,))

    @classmethod
    def tearDownClass(self) -> None:
        if self.is_imported(self):
            simple_pygame.quit((simple_pygame.TerminalModule,))

    def is_imported(self) -> bool:
        return simple_pygame.TerminalModule in self.successfully_imported

    def test_init(self) -> None:
        if not self.is_imported():
            self.skipTest("Import simple_pygame.terminal failed.")

        simple_pygame.quit((simple_pygame.TerminalModule,))
        self.assertIn(simple_pygame.TerminalModule, simple_pygame.init((simple_pygame.TerminalModule,)), "Import simple_pygame.terminal failed.")

if __name__ == "__main__":
    unittest.main()