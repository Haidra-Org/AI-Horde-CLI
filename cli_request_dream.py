#!/usr/bin/env python3
import requests
import json
import os
import time
import argparse
import base64
import yaml
import sys
from omegaconf import OmegaConf

from cli_logger import logger, set_logger_verbosity, quiesce_logger, test_logger
from PIL import Image
from io import BytesIO
from requests.exceptions import ConnectionError
from tqdm import tqdm

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument('-n', '--amount', action="store", required=False,
                        type=int, help="The amount of images to generate with this prompt")
arg_parser.add_argument("-m", '--model', action="store", default="stable_diffusion", required=False,
                        type=str, help="Generalist AI image generating model. The baseline for all finetuned models")
arg_parser.add_argument('-p', '--prompt', action="store", required=False,
                        type=str, help="The prompt with which to generate images")
arg_parser.add_argument('-w', '--width', action="store", required=False, type=int,
                        help="The width of the image to generate. Has to be a multiple of 64")
arg_parser.add_argument('-l', '--height', action="store", required=False, type=int,
                        help="The height of the image to generate. Has to be a multiple of 64")
arg_parser.add_argument('-s', '--steps', action="store", required=False,
                        type=int, help="The amount of steps to use for this generation")
arg_parser.add_argument('--api_key', type=str, action='store', required=False,
                        help="The API Key to use to authenticate on the Horde. Get one in https://aihorde.net/register")
arg_parser.add_argument('-f', '--filename', type=str, action='store', required=False,
                        help="The filename to use to save the images. If more than 1 image is generated, the number of generation will be prepended")
arg_parser.add_argument('-v', '--verbosity', action='count', default=0,
                        help="The default logging level is ERROR or higher. This value increases the amount of logging seen in your screen")
arg_parser.add_argument('-q', '--quiet', action='count', default=0,
                        help="The default logging level is ERROR or higher. This value decreases the amount of logging seen in your screen")
arg_parser.add_argument('--horde', action="store", required=False,
                        type=str, default="https://aihorde.net", help="Use a different horde")
arg_parser.add_argument('--nsfw', action="store_true", default=False, required=False,
                        help="Mark the request as NSFW. Only servers which allow NSFW will pick it up")
arg_parser.add_argument('--censor_nsfw', action="store_true", default=False, required=False,
                        help="If the request is SFW, and the worker accidentaly generates NSFW, it will send back a censored image.")
arg_parser.add_argument('--trusted_workers', action="store_true", default=False,
                        required=False, help="If true, the request will be sent only to trusted workers.")
arg_parser.add_argument('--source_image', action="store", required=False, type=str,
                        help="When a file path is provided, will be used as the source for img2img")
arg_parser.add_argument('--source_processing', action="store", required=False,
                        type=str, help="Can either be img2img, inpainting, or outpainting")
arg_parser.add_argument('--source_mask', action="store", required=False, type=str,
                        help="When a file path is provided, will be used as the mask source for inpainting/outpainting")
arg_parser.add_argument('--dry_run', action="store_true", default=False, required=False,
                        help="If true, The request will only print the amount of kudos the payload would spend, and exit.")
arg_parser.add_argument('--yml_file', action="store", default="cliRequestsData_Dream.yml",
                        required=False, help="Overrides the default yml, CLI arguments still have priority.")
arg_parser.add_argument('-b', '--progress_bar', action="store_true", required=False,
                        default=True, help="Show the progress bar")
args = arg_parser.parse_args()


class RequestData(object):
    def __init__(self):
        self.client_agent = "cli_request_dream.py:1.1.0:(discord)db0#1625"
        self.api_key = "0000000000"
        self.filename = "witch_dream.png"
        self.imgen_params = {
            "n": 2,
            "width": 64*8,
            "height": 64*8,
            "steps": 20,
            "sampler_name": "k_euler_a",
            "cfg_scale": 7.5,
            "denoising_strength": 0.6,
        }
        self.submit_dict = {
            "prompt": "a horde of cute stable robots in a sprawling server room repairing a massive mainframe",
            "nsfw": False,
            "censor_nsfw": False,
            "trusted_workers": False,
            "models": ["stable_diffusion"],
            "r2": True,
            "dry_run": False
        }
        self.source_image = None
        self.source_processing = "img2img"
        self.source_mask = None

    def get_submit_dict(self):
        submit_dict = self.submit_dict.copy()
        submit_dict["params"] = self.imgen_params
        submit_dict["source_processing"] = self.source_processing
        if self.source_image:
            final_src_img = Image.open(self.source_image)
            buffer = BytesIO()
            # We send as WebP to avoid using all the horde bandwidth
            final_src_img.save(buffer, format="Webp", quality=95, exact=True)
            submit_dict["source_image"] = base64.b64encode(
                buffer.getvalue()).decode("utf8")
        if self.source_mask:
            final_src_mask = Image.open(self.source_mask)
            buffer = BytesIO()
            # We send as WebP to avoid using all the horde bandwidth
            final_src_mask.save(buffer, format="Webp", quality=95, exact=True)
            submit_dict["source_mask"] = base64.b64encode(
                buffer.getvalue()).decode("utf8")
        return (submit_dict)


def load_request_data():
    request_data = RequestData()
    if os.path.exists(args.yml_file):
        with open(args.yml_file, "rt", encoding="utf-8", errors="ignore") as configfile:
            config = yaml.safe_load(configfile)
            for key, value in config.items():
                setattr(request_data, key, value)
    if os.path.exists("special.yml"):
        special = OmegaConf.load("special.yml")
        request_data.imgen_params["special"] = OmegaConf.to_container(
            special, resolve=True)
    if os.path.exists("special.json"):
        special = OmegaConf.load("special.json")
        request_data.imgen_params["special"] = OmegaConf.to_container(
            special, resolve=True)
    if args.api_key:
        request_data.api_key = args.api_key
    if args.filename:
        request_data.filename = args.filename
    if args.amount:
        request_data.imgen_params["n"] = args.amount
    if args.width:
        request_data.imgen_params["width"] = args.width
    if args.height:
        request_data.imgen_params["height"] = args.height
    if args.steps:
        request_data.imgen_params["steps"] = args.steps
    if args.prompt:
        request_data.submit_dict["prompt"] = args.prompt
    if args.nsfw:
        request_data.submit_dict["nsfw"] = args.nsfw
    if args.censor_nsfw:
        request_data.submit_dict["censor_nsfw"] = args.censor_nsfw
    if args.trusted_workers:
        request_data.submit_dict["trusted_workers"] = args.trusted_workers
    if args.source_image:
        request_data.source_image = args.source_image
    if args.source_processing:
        request_data.source_processing = args.source_processing
    if args.source_mask:
        request_data.source_mask = args.source_mask
    if args.dry_run:
        request_data.submit_dict["dry_run"] = args.dry_run
    return (request_data)


@logger.catch(reraise=True)
def generate():
    request_data = load_request_data()
    # final_submit_dict["source_image"] = 'Test'

    progress_bar = args.progress_bar
    if args.verbosity and progress_bar:
        progress_bar = False
    if progress_bar:
        pbar_queue_position = tqdm(desc="queue position: N/A | Wait Time: N/A",bar_format="{desc}")
        pbar_progress = tqdm(
            total=request_data.imgen_params.get('n'), desc="progress")

    headers = {
        "apikey": request_data.api_key,
        "Client-Agent": request_data.client_agent,
    }
    # logger.debug(request_data.get_submit_dict())
    # logger.debug(json.dumps(request_data.get_submit_dict(), indent=4))
    submit_req = requests.post(f'{args.horde}/api/v2/generate/async',
                               json=request_data.get_submit_dict(), headers=headers)
    if submit_req.ok:
        submit_results = submit_req.json()
        logger.debug(submit_results)
        req_id = submit_results.get('id')
        if not req_id:
            logger.message(submit_results)
            return
        is_done = False
        retry = 0
        cancelled = False
        try:
            while not is_done:
                try:
                    chk_req = requests.get(
                        f'{args.horde}/api/v2/generate/check/{req_id}')
                    if not chk_req.ok:
                        logger.error(chk_req.text)
                        return
                    chk_results = chk_req.json()
                    logger.info(chk_results)

                    if progress_bar:
                        pbar_progress.desc = (
                            f"Wait:{chk_results.get('waiting')} "
                            f"Proc:{chk_results.get('processing')} "
                            f"Res:{chk_results.get('restarted')} "
                            f"Fin:{chk_results.get('finished')}"
                        )
                        pbar_queue_position.desc = f"Queue Position: {chk_results.get('queue_position')} | ETA: {chk_results.get('wait_time')}s"
                        pbar_progress.n = chk_results.get('finished')

                        pbar_queue_position.refresh()
                        pbar_progress.refresh()

                    is_done = chk_results['done']
                    time.sleep(0.8)
                except ConnectionError as e:
                    retry += 1
                    logger.error(
                        f"Error {e} when retrieving status. Retry {retry}/10")
                    if retry < 10:
                        time.sleep(1)
                        continue
                    raise
        except KeyboardInterrupt:
            logger.info(f"Cancelling {req_id}...")
            cancelled = True
            retrieve_req = requests.delete(
                f'{args.horde}/api/v2/generate/status/{req_id}')
        if not cancelled:
            retrieve_req = requests.get(
                f'{args.horde}/api/v2/generate/status/{req_id}')
        if not retrieve_req.ok:
            logger.error(retrieve_req.text)
            return
        results_json = retrieve_req.json()
        # logger.debug(results_json)
        if results_json['faulted']:
            final_submit_dict = request_data.get_submit_dict()
            if "source_image" in final_submit_dict:
                final_submit_dict[
                    "source_image"] = f"img2img request with size: {len(final_submit_dict['source_image'])}"
            logger.error(
                f"Something went wrong when generating the request. Please contact the horde administrator with your request details: {final_submit_dict}")
            return
        results = results_json['generations']
        if progress_bar:
            pbar_queue_position.close()
            pbar_progress.close()
        for iter in range(len(results)):
            final_filename = request_data.filename
            if len(results) > 1:
                final_filename = f"{iter}_{request_data.filename}"
            if request_data.get_submit_dict()["r2"]:
                logger.debug(
                    f"Downloading '{results[iter]['id']}' from {results[iter]['img']}")
                try:
                    img_data = requests.get(results[iter]["img"]).content
                except:
                    logger.error("Received b64 again")
                with open(final_filename, 'wb') as handler:
                    handler.write(img_data)
            else:
                b64img = results[iter]["img"]
                base64_bytes = b64img.encode('utf-8')
                img_bytes = base64.b64decode(base64_bytes)
                img = Image.open(BytesIO(img_bytes))
                img.save(final_filename)
            censored = ''
            if results[iter]["censored"]:
                censored = " (censored)"
            logger.message(
                f"Saved{censored} {final_filename} for {results_json['kudos']} kudos (via {results[iter]['worker_id']})")
    else:
        logger.error(submit_req.text)


set_logger_verbosity(args.verbosity)
quiesce_logger(args.quiet)
generate()
