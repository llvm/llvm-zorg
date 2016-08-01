def stripQuotationMarks(s):
    '''
    I remove surraunding quotation marks from the given string, if any.
    Return the original unchnaged string otherwise.
    '''
    if (s[0] == s[-1]) and s.startswith(('\"', '\'')):
        return s[1:-1] # Strip the quotation marks.
    else:
        return s # Return the string unchanged.
