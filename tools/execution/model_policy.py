"""Explicit, secret-free model selection. Importing this module starts nothing."""
from __future__ import annotations

import json
import re
import sys
from urllib.parse import urlsplit

from .core import ROOT, Blocked, json_read, stable

ROLES = ('developer', 'code_review', 'test_engineer', 'test_review',
         'browser_planner', 'browser_review')
EFFORTS = {'none', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max', 'ultra'}
POLICY_PATH = ROOT / 'execution/agent-models.json'


def keys(value, allowed, required=None):
    if not isinstance(value, dict) or not set(value) <= set(allowed):
        raise Blocked('Unknown model-policy field; credentials and arbitrary CLI flags are forbidden')
    if not set(required or ()) <= set(value):
        raise Blocked('Missing model-policy field')


def validate(policy, known_tasks):
    keys(policy, {'schema', 'default_preset', 'preflight_ttl_seconds',
                  'preflight_timeout_seconds', 'providers', 'profiles',
                  'presets', 'ticket_overrides'},
         {'schema', 'default_preset', 'preflight_ttl_seconds',
          'preflight_timeout_seconds', 'providers', 'profiles', 'presets', 'ticket_overrides'})
    if type(policy['schema']) is not int or policy['schema'] != 1:
        raise Blocked('Unsupported model-policy schema')
    for key, limit in [('preflight_ttl_seconds', 3600), ('preflight_timeout_seconds', 600)]:
        if type(policy[key]) is not int or not 1 <= policy[key] <= limit:
            raise Blocked('Invalid bounded model preflight setting: ' + key)
    for key in ('providers', 'profiles', 'presets', 'ticket_overrides'):
        if not isinstance(policy[key], dict):
            raise Blocked('Model-policy maps must be objects')
    for name, provider in policy['providers'].items():
        if not re.fullmatch(r'[a-z][a-z0-9_-]*', name):
            raise Blocked('Invalid provider name')
        if not isinstance(provider, dict):
            raise Blocked('Provider must be an object')
        if provider.get('kind') == 'builtin':
            keys(provider, {'kind', 'provider_id'}, {'kind', 'provider_id'})
            if provider['provider_id'] != 'openai':
                raise Blocked('Unsupported builtin provider')
        elif provider.get('kind') == 'responses':
            keys(provider, {'kind', 'base_url', 'api_key_env'}, {'kind', 'base_url', 'api_key_env'})
            if not isinstance(provider['base_url'], str) or not isinstance(provider['api_key_env'], str):
                raise Blocked('Router URL and credential variable name must be strings')
            try:
                url = urlsplit(provider['base_url'])
            except ValueError as error:
                raise Blocked('Invalid router URL') from error
            if (url.scheme != 'https' or not url.hostname or url.username or url.password
                    or url.query or url.fragment or provider['base_url'].endswith('/')):
                raise Blocked('Router requires an HTTPS base URL without credentials/query/fragment/trailing slash')
            if not re.fullmatch(r'[A-Z][A-Z0-9_]*', provider['api_key_env']):
                raise Blocked('Only an environment-variable NAME may configure router authentication')
        else:
            raise Blocked('Unknown provider kind')
    for name, profile in policy['profiles'].items():
        keys(profile, {'provider', 'model', 'reasoning_effort'}, {'provider', 'model', 'reasoning_effort'})
        if not isinstance(profile['provider'], str) or profile['provider'] not in policy['providers']:
            raise Blocked('Unknown provider in profile: ' + name)
        if not isinstance(profile['model'], str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}', profile['model']):
            raise Blocked('Invalid explicit model ID')
        if not isinstance(profile['reasoning_effort'], str) or profile['reasoning_effort'] not in EFFORTS:
            raise Blocked('Invalid explicit reasoning effort')
    for mapping in policy['presets'].values():
        keys(mapping, ROLES, ROLES)
        if any(not isinstance(p, str) or p not in policy['profiles'] for p in mapping.values()):
            raise Blocked('Unknown model profile in preset')
    if not isinstance(policy['default_preset'], str) or policy['default_preset'] not in policy['presets']:
        raise Blocked('Unknown default model preset')
    if not set(policy['ticket_overrides']) <= set(known_tasks):
        raise Blocked('Model override references an unknown ticket')
    for ticket in policy['ticket_overrides'].values():
        keys(ticket, {'default', 'roles'})
        keys(ticket.get('roles', {}), ROLES)
        for override in [ticket.get('default', {}), *ticket.get('roles', {}).values()]:
            keys(override, {'profile', 'reasoning_effort'})
            if 'profile' in override and (not isinstance(override['profile'], str) or override['profile'] not in policy['profiles']):
                raise Blocked('Unknown override profile')
            if 'reasoning_effort' in override and (not isinstance(override['reasoning_effort'], str) or override['reasoning_effort'] not in EFFORTS):
                raise Blocked('Unknown override reasoning effort')
    return policy


def load(known_tasks):
    return validate(json_read(POLICY_PATH), known_tasks)


def resolve(policy, preset, task_id, role):
    preset = preset or policy['default_preset']
    if preset not in policy['presets'] or role not in ROLES:
        raise Blocked('Unknown model preset or role')
    profile_name = policy['presets'][preset][role]
    profile = dict(policy['profiles'][profile_name])
    ticket = policy['ticket_overrides'].get(task_id, {})
    for override in [ticket.get('default', {}), ticket.get('roles', {}).get(role, {})]:
        if 'profile' in override:
            profile_name = override['profile']
            profile = dict(policy['profiles'][profile_name])
        if 'reasoning_effort' in override:
            profile['reasoning_effort'] = override['reasoning_effort']
    binding = {**profile, 'provider_config': policy['providers'][profile['provider']],
               'requires_image_input': role in ('browser_planner', 'browser_review')}
    return {**binding, 'profile': profile_name, 'preset': preset,
            'selection_sha256': stable(binding), 'policy_sha256': stable(policy)}


def selections(policy, preset, selected):
    if (preset or policy['default_preset']) not in policy['presets']:
        raise Blocked('Unknown model preset')
    return [{'task': task['id'], 'role': role, **resolve(policy, preset, task['id'], role)}
            for task in selected if task['kind'] != 'readiness' for role in ROLES]


def cli_args(selection):
    """Explicit CLI settings override inherited model defaults, never permissions."""
    args = ['--model', selection['model'], '-c',
            'model_reasoning_effort=' + json.dumps(selection['reasoning_effort'])]
    provider = selection['provider_config']
    if provider['kind'] == 'builtin':
        return args + ['-c', 'model_provider="openai"']
    # A private namespace avoids merging with unrelated user provider definitions.
    provider_id = 'stone_router_' + stable(provider)[:16]
    settings = {
        'model_provider': provider_id,
        f'model_providers.{provider_id}.name': 'Stone Shelter router',
        f'model_providers.{provider_id}.base_url': provider['base_url'],
        f'model_providers.{provider_id}.wire_api': 'responses',
        f'model_providers.{provider_id}.auth.command': sys.executable,
        f'model_providers.{provider_id}.auth.args': [str(ROOT / 'tools/provider_key.py'), provider['api_key_env']],
    }
    for name, value in settings.items():
        args.extend(['-c', name + '=' + json.dumps(value)])
    return args
