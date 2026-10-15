"""cloud_explorer.py — AWS Academy Cloud Foundations, Modules 3, 4 and 6.

Credentials are read from a ``.env`` file next to this script (see
``.env.example``). Paste the values from "AWS Details > AWS CLI" there.

    pip install boto3 python-dotenv
    python __main__.py            #* parts 1-3 (no cost)
    python __main__.py --launch   # also part 4 (launches and terminates a t3.micro)
"""

from __future__ import annotations

import argparse
import fnmatch
from pathlib import Path
from typing import Any

import boto3
from dotenv import load_dotenv

# Load AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY and AWS_SESSION_TOKEN from the
# project's .env; override=True so a fresh lab session always wins.
load_dotenv(Path(__file__).with_name(".env"), override=True)

REGION: str = "us-east-1"  # Learner Lab allows us-east-1 and us-west-2 only

Policy = dict[str, Any]


# * ---------------------------------------------------------------------------
# * Part 1 — Module 3: Regions and Availability Zones
# * ---------------------------------------------------------------------------
def list_regions() -> list[str]:
    """Return the names of the Regions enabled for this account.

    Returns:
        Sorted list of Region names, e.g. ``["eu-south-2", "us-east-1"]``.
    """
    ec2 = boto3.client("ec2", region_name=REGION)
    # TODO 1: call describe_regions() and return the sorted RegionName values.

    region_names = sorted(
        region["RegionName"] for region in ec2.describe_regions()["Regions"]
    )

    return region_names


def list_availability_zones(region: str) -> list[tuple[str, str]]:
    """Return the Availability Zones of a Region.

    Args:
        region: Region name, e.g. ``"us-east-1"``.

    Returns:
        List of ``(zone_name, zone_id)`` tuples.
    """
    ec2 = boto3.client("ec2", region_name=region)
    # TODO 2: call describe_availability_zones() and return (ZoneName, ZoneId) pairs.

    zones = [
        (z["ZoneName"], z["ZoneId"])
        for z in ec2.describe_availability_zones()["AvailabilityZones"]
    ]

    return zones


# * ---------------------------------------------------------------------------
# * Part 2 — Module 4: who am I? (authentication with a role)
# * ---------------------------------------------------------------------------
def who_am_i() -> dict[str, str]:
    """Return the identity behind the current credentials.

    Returns:
        Dict with ``Account``, ``Arn`` and ``UserId`` from STS.
    """
    sts = boto3.client("sts", region_name=REGION)
    # TODO 3: call sts.get_caller_identity(). Is the ARN a user or an assumed role?
    identity = sts.get_caller_identity()
    keys = ["Account", "Arn", "UserId"]
    return {k: identity[k] for k in keys}


# * ---------------------------------------------------------------------------
# * Part 3 — Module 4: a tiny IAM policy evaluator (runs offline)
# * ---------------------------------------------------------------------------
def _as_list(value: str | list[str]) -> list[str]:
    """Normalize a policy field that may be a string or a list."""
    return [value] if isinstance(value, str) else value


def _matches(patterns: list[str], value: str) -> bool:
    """Case-insensitive wildcard match used for actions and resources."""
    return any(fnmatch.fnmatchcase(value.lower(), p.lower()) for p in patterns)


def _statement_applies(statement: dict[str, Any], action: str, resource: str) -> bool:
    """Check whether one statement covers the action and resource.

    Supports ``Action``/``NotAction`` and ``Resource``/``NotResource``.
    """
    if "Action" in statement:
        action_ok = _matches(_as_list(statement["Action"]), action)
    else:
        action_ok = not _matches(_as_list(statement["NotAction"]), action)
    if "Resource" in statement:
        resource_ok = _matches(_as_list(statement["Resource"]), resource)
    else:
        resource_ok = not _matches(_as_list(statement["NotResource"]), resource)
    return action_ok and resource_ok


def evaluate(policies: list[Policy], action: str, resource: str) -> str:
    """Evaluate identity-based policies the way IAM does.

    Rule order: an explicit Deny always wins; otherwise an explicit Allow
    grants; otherwise the request is implicitly denied.

    Args:
        policies: IAM policy documents attached to the principal.
        action: Requested action, e.g. ``"s3:GetObject"``.
        resource: Requested resource ARN.

    Returns:
        ``"ExplicitDeny"``, ``"Allow"`` or ``"ImplicitDeny"``.
    """
    # TODO 4: implement the three rules from the Module 4 flowchart.
    # Hint: loop over every statement of every policy; use _statement_applies().

    effects = {
        statement["Effect"]
        for policy in policies
        for statement in policy["Statement"]
        if _statement_applies(statement, action, resource)
    }

    if "Deny" in effects:
        return "ExplicitDeny"
    if "Allow" in effects:
        return "Allow"
    return "ImplicitDeny"


# Policy from the Module 4 slides: full access to one table and one bucket only.
SLIDE_POLICY: Policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": ["dynamodb:*", "s3:*"],
            "Resource": [
                "arn:aws:dynamodb:us-east-1:123456789012:table/Grades",
                "arn:aws:s3:::deusto-photos",
                "arn:aws:s3:::deusto-photos/*",
            ],
        },
        {
            "Effect": "Deny",
            "Action": ["dynamodb:*", "s3:*"],
            "NotResource": [
                "arn:aws:dynamodb:us-east-1:123456789012:table/Grades",
                "arn:aws:s3:::deusto-photos",
                "arn:aws:s3:::deusto-photos/*",
            ],
        },
    ],
}

TEST_CASES: list[tuple[str, str, str]] = [
    ("s3:GetObject", "arn:aws:s3:::deusto-photos/cat.jpg", "Allow"),
    ("s3:GetObject", "arn:aws:s3:::another-bucket/cat.jpg", "ExplicitDeny"),
    (
        "dynamodb:PutItem",
        "arn:aws:dynamodb:us-east-1:123456789012:table/Grades",
        "Allow",
    ),
    (
        "ec2:TerminateInstances",
        "arn:aws:ec2:us-east-1:123456789012:instance/i-0abc",
        "ImplicitDeny",
    ),
]


def run_policy_tests() -> None:
    """Print the evaluator result for each test case and check it."""
    for action, resource, expected in TEST_CASES:
        result = evaluate([SLIDE_POLICY], action, resource)
        # ANSI colors: green for OK, red for BAD; \033[0m resets the color.
        mark = "\033[32mOK \033[0m" if result == expected else "\033[31mBAD\033[0m"
        print(f"  [{mark}] {action:<24} {resource:<60} -> {result}")


# * ---------------------------------------------------------------------------
# * Part 4 — Module 6: EC2 instance lifecycle (optional, --launch)
# * ---------------------------------------------------------------------------
USER_DATA: str = """#!/bin/bash
dnf install -y httpd
echo "<h1>Hello from $(hostname -f)</h1>" > /var/www/html/index.html
systemctl enable --now httpd
"""


def latest_amazon_linux_ami(region: str) -> str:
    """Find the newest Amazon Linux 2023 x86_64 AMI published by Amazon.

    Args:
        region: Region where the AMI will be used.

    Returns:
        The AMI ID.
    """
    ec2 = boto3.client("ec2", region_name=region)
    images = ec2.describe_images(
        Owners=["amazon"],
        Filters=[
            {"Name": "name", "Values": ["al2023-ami-2023*-x86_64"]},
            {"Name": "state", "Values": ["available"]},
        ],
    )["Images"]
    return max(images, key=lambda image: image["CreationDate"])["ImageId"]


def launch_and_terminate(region: str, student: str) -> None:
    """Walk an instance through pending -> running -> shutting-down -> terminated.

    Args:
        region: Region to launch in.
        student: Your name or ID, used in the ``Name`` tag.
    """
    ec2 = boto3.resource("ec2", region_name=region)
    ami = latest_amazon_linux_ami(region)
    # TODO 5: create one t3.micro with the AMI, USER_DATA and tags Name / Course.
    # Hint: ec2.create_instances(ImageId=..., InstanceType=..., MinCount=1, MaxCount=1,
    #       UserData=..., TagSpecifications=[...])
    (instance,) = ec2.create_instances(
        ImageId=ami,
        InstanceType="t3.micro",
        MinCount=1,
        MaxCount=1,
        UserData=USER_DATA,
        TagSpecifications=[
            {
                "ResourceType": "instance",
                "Tags": [
                    {
                        "Key": "Name",
                        "Value": student,
                    },
                    {
                        "Key": "Course",
                        "Value": "Cloud Computing",
                    },
                ],
            }
        ],
    )
    try:
        print(f"  launched {instance.id} from {ami}, state={instance.state['Name']}")
        instance.wait_until_running()
        instance.reload()
        print(f"  running in AZ {instance.placement['AvailabilityZone']}")
        print(
            f"  public IP {instance.public_ip_address}, private IP {instance.private_ip_address}"
        )
    finally:
        # TODO 6: terminate the instance and wait until it is terminated.
        # Hint: do it in a finally block so it runs even if something fails.
        instance.terminate()
        instance.wait_until_terminated()
        print(f"  {instance.id} terminated")


def main() -> None:
    """Run all parts of the exercise."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--launch", action="store_true", help="run part 4 (EC2)")
    parser.add_argument("--student", default="student", help="name for the Name tag")
    parser.add_argument("--offline", action="store_true", help="only run part 3")
    args = parser.parse_args()

    if not args.offline:
        print("=" * 45)
        print("Part 1 — Regions and AZs")
        print("=" * 45)
        print("\n")
        regions = list_regions()
        print(f"  {len(regions)} Regions enabled: {', '.join(regions)}")
        print("\n")
        for name, zone_id in list_availability_zones(REGION):
            print(f"  {REGION}: {name} ({zone_id})")

        print("\n")
        print("=" * 45)
        print("Part 2 — Who am I?")
        print("=" * 45)
        print("\n")
        for key, value in who_am_i().items():
            print(f"  {key}: {value}")

    print("\n")
    print("=" * 45)
    print("Part 3 — IAM policy evaluation")
    print("=" * 45)
    print("\n")
    run_policy_tests()

    if args.launch and not args.offline:
        print("\n")
        print("=" * 45)
        print("Part 4 — EC2 lifecycle")
        print("=" * 45)
        print("\n")
        launch_and_terminate(REGION, args.student)


if __name__ == "__main__":
    main()
