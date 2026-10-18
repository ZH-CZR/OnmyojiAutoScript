"""Public channel login templates; provenance: upstream/login_device_port.json."""
from module.atom.image import RuleImage


class LoginChannelAssets:
    I_QD_READ_AND_AGREED = RuleImage(
        file='qd4399/qd_read_and_agreed.png', path='./tasks/Restart/',
        roi_front=(693, 520, 191, 54), roi_back=(192, 28, 860, 620),
        threshold=0.8, method='Template matching')
    I_ACCEPT_AGREEMENT = RuleImage(
        file='qd4399/accept_agreement.png', path='./tasks/Restart/',
        roi_front=(751, 603, 76, 31), roi_back=(673, 581, 237, 73),
        threshold=0.8, method='Template matching')
