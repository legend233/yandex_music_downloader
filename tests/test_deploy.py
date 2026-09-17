import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import traceback
import unittest
from unittest.mock import patch
import urllib.error
import urllib.parse


spec = importlib.util.spec_from_file_location(
    "deploy", Path(__file__).resolve().parents[1] / "scripts" / "deploy.py"
)
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)


class DeployTests(unittest.TestCase):
    def setUp(self):
        self.env = {"PORTAINER_URL": "https://portainer.invalid/",
                    "PORTAINER_API_TOKEN": "secret-token"}
        self.enterContext(patch.dict(os.environ, self.env, clear=True))
        self.http = self.enterContext(patch.object(deploy.urllib.request, "urlopen"))
        self.clock = self.enterContext(patch.object(deploy.time, "monotonic", return_value=0))
        self.sleep = self.enterContext(patch.object(deploy.time, "sleep"))
        self.output = self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.definition = "services:\n  app:\n    image: app:latest\n# secret-definition\n"
        self.stack_env = [{"name": "PASSWORD", "value": "secret-env"},
                          {"name": "EMPTY", "value": ""}]
        self.stack = {"Id": 17, "Name": "yandexdownloader", "EndpointId": 5,
                      "Env": self.stack_env, "Status": 1}

    def responses(self, *values):
        responses = []
        for value in values:
            response = unittest.mock.MagicMock()
            response.__enter__.return_value.read.return_value = json.dumps(value).encode()
            responses.append(response)
        self.http.side_effect = responses

    def discovery(self):
        return ([{"Id": 2, "Name": "other"}, {"Id": 5, "Name": "pve-2-docker"}],
                [dict(self.stack, Id=99, EndpointId=2), self.stack])

    def test_defaults_endpoint_filter_and_read_only_dry_run(self):
        self.assertEqual(deploy.DEFAULT_STACK_NAME, "yandexdownloader")
        self.assertEqual(deploy.DEFAULT_ENDPOINT_NAME, "pve-2-docker")
        self.responses(*self.discovery())
        self.assertEqual(deploy.main(["--dry-run"]), 0)
        self.assertEqual(self.http.call_count, 2)
        for call in self.http.call_args_list:
            self.assertEqual(call.args[0].get_method(), "GET")
        url = self.http.call_args.args[0].full_url
        filters = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)["filters"][0]
        self.assertEqual(json.loads(filters), {"EndpointID": 5})
        self.sleep.assert_not_called()

    def test_update_preserves_definition_env_flags_and_timeout600(self):
        self.responses(*self.discovery(), {"StackFileContent": self.definition},
                       None, {"Status": 3}, {"Status": 1})
        self.assertEqual(deploy.main([]), 0)
        call = self.http.call_args_list[3]
        request = call.args[0]
        self.assertEqual(request.get_method(), "PUT")
        self.assertEqual(request.full_url, "https://portainer.invalid/api/stacks/17?endpointId=5")
        self.assertEqual(request.get_header("X-api-key"), "secret-token")
        self.assertEqual(call.kwargs["timeout"], 600)
        self.assertEqual(json.loads(request.data), {
            "StackFileContent": self.definition, "Env": self.stack_env,
            "Prune": False, "PullImage": True, "RepullImageAndRedeploy": True,
        })
        self.sleep.assert_called_once_with(3)
        self.assertNotIn("secret", self.output.getvalue())

    def test_stack_on_wrong_endpoint_is_rejected(self):
        self.responses([dict(self.stack, EndpointId=2)])
        with self.assertRaises(deploy.PortainerError):
            deploy._find_stack(self.env["PORTAINER_URL"], "secret-token", 5, "yandexdownloader")

    def test_active(self):
        self.responses({"Status": 1})
        deploy._wait_for_deploy("https://portainer.invalid", "secret-token", 17, 180)
        self.sleep.assert_not_called()

    def test_error_and_inactive_do_not_expose_deployment_messages(self):
        for status in (2, 4):
            with self.subTest(status=status):
                self.responses({"Status": status,
                                "DeploymentStatus": [{"Message": "secret-env secret-token"}]})
                with self.assertRaises(deploy.PortainerError) as error:
                    deploy._wait_for_deploy("https://portainer.invalid", "secret-token", 17, 180)
                self.assertNotIn("secret", str(error.exception))
        self.sleep.assert_not_called()

    def test_timeout(self):
        self.responses({"Status": 3}, {"Status": 3})
        self.clock.side_effect = [0, 0, 3, 6]
        with self.assertRaisesRegex(deploy.PortainerError, "within 6s"):
            deploy._wait_for_deploy("https://portainer.invalid", "secret-token", 17, 6)
        self.assertEqual(self.sleep.call_count, 2)

    def test_missing_required_environment(self):
        for name in ("PORTAINER_URL", "PORTAINER_API_TOKEN"):
            with self.subTest(name=name), patch.dict(os.environ, {name: "  "}):
                with self.assertRaisesRegex(deploy.PortainerError, name):
                    deploy.main([])
        self.http.assert_not_called()

    def test_missing_stack_env_prevents_update(self):
        del self.stack["Env"]
        self.responses(*self.discovery())
        with self.assertRaisesRegex(deploy.PortainerError, "missing Env"):
            deploy.main([])
        self.assertEqual(self.http.call_count, 2)

    def test_http_error_does_not_expose_token_body_or_exception_chain(self):
        body = io.BytesIO(b"secret-env")
        self.http.side_effect = urllib.error.HTTPError(
            "https://portainer.invalid/secret-token", 500, "secret-token", {}, body
        )
        with self.assertRaises(deploy.PortainerError) as error:
            deploy._request("https://portainer.invalid", "secret-token", "GET", "/api/stacks")
        formatted = "".join(traceback.format_exception(error.exception))
        self.assertIn("HTTP 500", formatted)
        self.assertNotIn("secret", formatted)
        self.assertEqual(body.tell(), 0)

    def test_transport_error_is_sanitized(self):
        self.http.side_effect = urllib.error.URLError("secret-token secret-env")
        with self.assertRaises(deploy.PortainerError) as error:
            deploy._request("https://portainer.invalid", "secret-token", "GET", "/api/stacks")
        self.assertNotIn("secret", "".join(traceback.format_exception(error.exception)))


if __name__ == "__main__":
    unittest.main()
