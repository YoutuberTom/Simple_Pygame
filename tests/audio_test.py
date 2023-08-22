import simple_pygame, unittest, time, subprocess, sys, os

class TestAudio(unittest.TestCase):
    @classmethod
    def setUpClass(self) -> None:
        self.file_path = os.path.join(os.path.join(os.path.dirname(sys.argv[0])), "data", "Sound.mp3")
        self.successfully_initialized = simple_pygame.mixer.init([simple_pygame.AudioClass])

        if self.is_initialized(self):
            self.audio = simple_pygame.mixer.Audio(self.file_path)

    @classmethod
    def tearDownClass(self) -> None:
        if self.is_initialized(self):
            self.audio.terminate()

        simple_pygame.mixer.quit([simple_pygame.AudioClass])

    def is_initialized(self) -> bool:
        return simple_pygame.AudioClass in self.successfully_initialized

    def test_get_information(self) -> None:
        if not self.is_initialized():
            self.skipTest("Import simple_pygame.mixer.Audio failed.")

        try:
            self.assertEqual(type(self.audio.get_information(self.audio.path)), dict, "The return value must be a dict.")
        except FileNotFoundError:
            self.skipTest("No ffprobe found.")
        except Exception as exception:
            self.fail(exception)

        try:
            self.assertEqual(type(self.audio.get_information(self.audio.path, encoding = "encoding")), dict, "The return value must be a dict.")
        except FileNotFoundError:
            self.skipTest("No ffprobe found.")
        except ValueError:
            pass
        except Exception as exception:
            self.fail(exception)

        try:
            self.assertEqual(type(self.audio.get_information(self.audio.path, "utf-8", True, "ffmpeg")), dict, "The return value must be a dict.")
        except FileNotFoundError:
            self.skipTest("No ffmpeg found.")
        except Exception as exception:
            self.fail(exception)

    def test_create_pipe(self) -> None:
        if not self.is_initialized():
            self.skipTest("Import simple_pygame.mixer.Audio failed.")

        try:
            pipe, information, stream_information = self.audio.create_pipe(self.audio.path, stream = -1)
        except Exception as exception:
            self.fail(exception)

        self.assertEqual(type(pipe), subprocess.Popen, "Pipe must be a subprocess.Popen object.")
        self.assertEqual(type(information), dict, "Information must be a dict.")
        self.assertEqual(type(stream_information), dict, "Stream information must be a dict.")

        self.assertEqual(stream_information["index"], 0, "Invalid stream index.")
        self.assertDictEqual(self.audio.get_specific_codec_type(information, simple_pygame.AudioType)[0], stream_information, "Invalid stream information.")

        pipe.stdout.close()
        pipe.terminate()
        pipe.wait()

    def test_change_attributes(self) -> None:
        if not self.is_initialized():
            self.skipTest("Import simple_pygame.mixer.Audio failed.")

        try:
            self.audio.change_attributes(encoding = True)
        except TypeError:
            pass
        except Exception as exception:
            self.fail(exception)

        try:
            self.audio.change_attributes(chunk = -1)
        except ValueError:
            pass
        except Exception as exception:
            self.fail(exception)

    def test_set_format(self) -> None:
        if not self.is_initialized():
            self.skipTest("Import simple_pygame.mixer.Audio failed.")

        try:
            self.audio.set_format(simple_pygame.SInt32)
        except Exception as exception:
            self.fail(exception)

        try:
            self.audio.set_format("format")
        except ValueError:
            pass
        except Exception as exception:
            self.fail(exception)

    def test_device(self) -> None:
        if not self.is_initialized():
            self.skipTest("Import simple_pygame.mixer.Audio failed.")

        try:
            self.audio.get_device_info(-1)
        except ValueError:
            pass
        except Exception as exception:
            self.fail(exception)

        try:
            current_device_information = self.audio.get_device_info()
            for device_index in range(self.audio.get_device_count()):
                device_information = self.audio.get_device_info(device_index) 
                if device_information != current_device_information["index"] and device_information["maxOutputChannels"] != 0:
                    self.audio.set_output_device_by_index(device_information["index"])
                    break

            self.audio.set_output_device_by_index()
        except ValueError:
            pass
        except Exception as exception:
            self.fail(exception)

        self.assertDictEqual(self.audio.get_device_info(), current_device_information, "Invalid device information.")

    def test_play(self) -> None:
        if not self.is_initialized():
            self.skipTest("Import simple_pygame.mixer.Audio failed.")

        self.assertEqual(self.audio.get_position(), simple_pygame.AudioEnded, "Invalid audio position.")

        self.audio.play()
        self.assertTrue(self.audio.get_busy(), "Play audio failed.")
        self.assertEqual(self.audio.get_position(), simple_pygame.AudioIsLoading, "Invalid audio position.")

        time.sleep(0.1)

        self.audio.pause()
        self.assertTrue(self.audio.get_pause(), "Pause audio failed.")

        while self.audio._pause_offset == None:
            time.sleep(0.1)
        before_position = self.audio.get_position()

        time.sleep(0.1)

        after_position = self.audio.get_position()
        self.assertEqual(before_position, after_position, "Invalid audio position.")

        self.audio.set_position(1)
        while self.audio._reposition:
            time.sleep(0.1)
        self.assertEqual(self.audio.get_position(), 1, "Invalid audio position.")

        self.audio.resume()
        self.assertFalse(self.audio.get_pause(), "Resume audio failed.")

        self.audio.set_position(2)
        while self.audio._reposition:
            time.sleep(0.1)
        self.assertLessEqual(2, self.audio.get_position(), "Invalid audio position.")

        self.audio.stop()
        self.assertFalse(self.audio.get_busy(), "Stop audio failed.")
        self.assertEqual(self.audio.get_position(), simple_pygame.AudioEnded, "Invalid audio position.")

    def test_join(self) -> None:
        if not self.is_initialized():
            self.skipTest("Import simple_pygame.mixer.Audio failed.")

        self.audio.play()
        self.assertTrue(self.audio.get_busy(), "Play audio failed.")
        self.assertEqual(self.audio.get_position(), simple_pygame.AudioIsLoading, "Invalid audio position.")

        self.audio.join()
        self.assertFalse(self.audio.get_busy(), "Join audio failed..")
        self.assertEqual(self.audio.get_position(), simple_pygame.AudioEnded, "Invalid audio position.")

    def test_volume(self) -> None:
        if not self.is_initialized():
            self.skipTest("Import simple_pygame.mixer.Audio failed.")

        self.assertEqual(self.audio.get_volume(), 1, "Invalid volume.")
        self.audio.set_volume(1 / 3)
        self.assertEqual(self.audio.get_volume(), 1 / 3, "Invalid volume.")

    def test_get_exception(self) -> None:
        if not self.is_initialized():
            self.skipTest("Import simple_pygame.mixer.Audio failed.")

        self.audio.path = "path"

        self.audio.play()
        while self.audio.get_position() != simple_pygame.AudioEnded:
            time.sleep(0.1)

        try:
            self.audio.get_exception()
        except ValueError:
            pass
        except Exception as exception:
            self.fail(exception)

        self.audio.path = self.file_path

    def test_context_manager(self) -> None:
        if not self.is_initialized():
            self.skipTest("Import simple_pygame.mixer.Audio failed.")

        with simple_pygame.mixer.Audio(self.file_path) as audio:
            audio.play()

        self.assertFalse(audio.get_busy(), "Stop audio failed.")

    def test_convert(self) -> None:
        if not self.is_initialized():
            self.skipTest("Import simple_pygame.mixer.Audio failed.")

        self.assertEqual(self.audio.nanoseconds_to_seconds(123456789), 0.123456789, "Invalid time.")
        self.assertEqual(self.audio.seconds_to_nanoseconds(987654321), 987654321000000000, "Invalid time.")

if __name__ == "__main__":
    unittest.main()