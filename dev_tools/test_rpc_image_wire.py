"""RPC pixel transport and bind defaults; no listeners, OCR models or devices."""
import pickle
import struct
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from module.image import rpc as image_rpc
from module.image.runtime import ImageRuntime
from module.image.wire import IMAGE_PROTOCOL, decode_image, encode_image
from module.exception import ScriptError
from module.ocr import rpc as ocr_rpc


class ImageWireTest(unittest.TestCase):
    def test_pixel_roundtrip_preserves_grayscale_color_slices_and_dtype(self):
        for shape in ((12, 16), (12, 16, 1), (12, 16, 3), (12, 16, 4)):
            for dtype in ('u1', '<u2', '>u2', '<i4', '<f4', '<f8'):
                with self.subTest(shape=shape, dtype=dtype):
                    source = np.arange(np.prod(shape)).reshape(shape).astype(dtype)[::2, ::-1]
                    restored = decode_image(encode_image(source))
                    np.testing.assert_array_equal(restored, source)
                    self.assertTrue(restored.flags.c_contiguous)
                    self.assertTrue(restored.flags.writeable)
                    self.assertEqual(restored.dtype, source.dtype.newbyteorder('<'))

    def test_object_dtype_and_invalid_dimensions_rejected(self):
        for image in (np.array([[object()]]), np.zeros((1,)), np.zeros((0, 5)),
                      np.zeros((2, 2, 2)), np.zeros((8193, 1), dtype='u1')):
            with self.subTest(shape=image.shape), self.assertRaises((TypeError, ValueError)):
                encode_image(image)

    def test_legacy_pickle_and_malformed_packets_rejected_before_array_allocation(self):
        header = lambda code, dims, channels, flags, h, w: struct.pack(
            '!8sBBBBII', b'OASIMG1\0', code, dims, channels, flags, h, w)
        packets = (
            pickle.dumps(np.zeros((2, 2), dtype='u1')),
            b'bad',
            header(255, 2, 1, 0, 2, 2),
            header(0, 2, 1, 1, 2, 2),
            header(0, 2, 1, 0, 0, 2),
            header(0, 3, 3, 0, 8192, 8192),
            header(0, 2, 1, 0, 2, 2) + b'123',
            header(0, 2, 1, 0, 2, 2) + b'12345',
        )
        with patch('pickle.loads', side_effect=AssertionError('pickle must never execute')), \
                patch('numpy.frombuffer', side_effect=AssertionError('invalid header allocated pixels')):
            for packet in packets:
                with self.subTest(length=len(packet)), self.assertRaises(ValueError):
                    decode_image(packet)

    def test_image_client_runtime_frame_and_dynamic_template(self):
        runtime = ImageRuntime({'worker_count': 1})
        self.addCleanup(runtime.shutdown)
        client = image_rpc.ImageClient.__new__(image_rpc.ImageClient)
        client.client = runtime
        image = np.arange(12 * 16 * 3, dtype='u1').reshape(12, 16, 3)
        frame = client.register_frame(image, 'account_main')
        np.testing.assert_array_equal(runtime._resolve_image(frame['frame_id'], None), image)
        np.testing.assert_array_equal(
            runtime._resolve_image(None, client._encode_image_payload(image, None)), image)
        with patch.object(runtime, '_template_match_image', return_value=(True, 1.0, [0, 0, 4, 3])) as match:
            client.match_dynamic_template(image[:3, :4], frame_id=frame['frame_id'])
            np.testing.assert_array_equal(match.call_args.kwargs['template'], image[:3, :4])
            np.testing.assert_array_equal(match.call_args.kwargs['image'], image)
        self.assertIsNone(client._encode_image_payload(image, frame['frame_id']))

    def test_ocr_client_both_operations_share_safe_decoder(self):
        proxy = ocr_rpc.ModelProxy.__new__(ocr_rpc.ModelProxy)
        proxy.save_log = False
        proxy.model_size = 'medium'
        proxy._cache_enabled = Mock(return_value=False)
        source = np.arange(60, dtype='u1').reshape(4, 5, 3)

        def request(method, payload, *args):
            np.testing.assert_array_equal(ocr_rpc.OcrRuntime._decode_image(payload), source)
            return [] if method == 'detect_and_ocr' else ('test', 1.0)

        proxy._call_with_timeout_retry = Mock(side_effect=request)
        self.assertEqual(proxy.ocr_single_line(source), ('test', 1.0))
        self.assertEqual(proxy.detect_and_ocr(source), [])
        self.assertEqual(proxy._call_with_timeout_retry.call_count, 2)

    def test_client_handshake_rejects_legacy_services_and_closes_connections(self):
        for module, client_type in ((image_rpc, image_rpc.ImageClient), (ocr_rpc, ocr_rpc.ModelProxy)):
            for protocol in (None, IMAGE_PROTOCOL):
                with self.subTest(client=client_type.__name__, protocol=protocol), \
                        patch.object(module.zerorpc, 'Client') as factory:
                    factory.return_value.get_server_info.return_value = {'image_protocol': protocol}
                    if protocol is None:
                        with self.assertRaisesRegex(ScriptError, '协议不兼容'):
                            client_type('127.0.0.1:12345')
                        factory.return_value.close.assert_called_once()
                    else:
                        client_type('127.0.0.1:12345')
                        factory.return_value.close.assert_not_called()


class RpcBindTest(unittest.TestCase):
    def test_default_loopback_and_explicit_remote_binding_without_opening_ports(self):
        from module.server.setting import State
        for module, prefix, process_owner in (
            (image_rpc, 'Image', image_rpc._IMAGE_SERVER_CONTEXT),
            (ocr_rpc, 'Ocr', ocr_rpc.multiprocessing),
        ):
            for configured_host in (None, '0.0.0.0', '192.0.2.10'):
                with self.subTest(service=prefix, host=configured_host):
                    config = SimpleNamespace(**{f'Start{prefix}Server': True, f'{prefix}ServerPort': 12345})
                    if configured_host is not None:
                        setattr(config, f'{prefix}ServerHost', configured_host)
                    global_name = f'_{prefix.upper()}_SERVER_PROCESS'
                    with patch.object(State, '_deploy_config_', config, create=True), \
                            patch.object(module, global_name, None), \
                            patch.object(module, '_build_server_settings', return_value={}), \
                            patch.object(module, '_is_port_in_use', side_effect=[False, True]) as probe, \
                            patch.object(process_owner, 'Process') as process:
                        self.assertTrue(getattr(module, f'ensure_{prefix.lower()}_server_started')())
                        expected = configured_host or '127.0.0.1'
                        self.assertEqual(process.call_args.kwargs['args'][0], expected)
                        probe_host = '127.0.0.1' if expected == '0.0.0.0' else expected
                        self.assertEqual(probe.call_args.args[0], probe_host)
                        process.return_value.start.assert_called_once()


if __name__ == '__main__':
    unittest.main()
