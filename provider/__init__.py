class Analytics(object):

    def sort_by(self, c, attributes, reverse=False, max_results=None):
        result = sorted(c, key=lambda q: [getattr(q, x) for x in attributes], reverse=reverse)
        if isinstance(max_results, int):
            return result[:max_results]
        else:
            return result
