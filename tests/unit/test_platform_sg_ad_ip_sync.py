import os
import json

import pytest

from src.console_ext_login import prepare_email_body

def test_prepare_email_body():
    '''Happy path test for prepare_email_body'''
    source_ip_address = "10.0.0.1"
    event_time = "2022-10-19 11:52:02 PM"

    expected_body_html = f"""
        <html>
            <head></head>
            <body>
                <p>Hi,</p>
                <p>Our logs have indicated that you have accessed the MMM AWS portal from outside of the MMM network.</p>
                <p>
                    You IP address: {source_ip_address}
                    <br/>
                    Timestamp: {event_time}
                </p>
                <p>We would like to remind you that portal access from outside of the MMM network is against IT Security policy.</p>
                <p>If you experience difficulty in accessing the cloud portals inside the MMM network and need an exemption, please contact Security@mmm.gov.au</p><br/>
                <p>Regards,</p>
                <p>Cloud Services Group</p>
            </body>
        </html>
    """

    expected_body_text = (f"""Hi,\r\n
            Our logs have indicated that you have accessed the MMM AWS portal from outside of the MMM network.\r\n
            You IP address: {source_ip_address}\r\n
            Timestamp: {event_time}\r\n
            We would like to remind you that portal access from outside of the MMM network is against IT Security policy.\r\n
            If you experience difficulty in accessing the cloud portals inside the MMM network and need an exemption, please contact Security@mmm.gov.au\r\n\n
            Regards,\r\n
            Cloud Services Group\r\n
            """)

    actual_body_html, actual_body_text = prepare_email_body(source_ip_address, event_time)

    assert expected_body_html == actual_body_html
    assert expected_body_text == actual_body_text
