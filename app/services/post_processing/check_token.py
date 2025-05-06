SINHALA_ZWJ = '\u200D'
SINHALA_HALKIRIMA = '\u0DCA'

SINHALA_RA = '\u0DBB'
SINHALA_YA = '\u0DBA'

def needs_zwj(prev_token, curr_token):
    if not prev_token or not curr_token:
        return False

    if prev_token[-1] == SINHALA_HALKIRIMA and curr_token[0] in (SINHALA_RA, SINHALA_YA):
        return True
    return False
