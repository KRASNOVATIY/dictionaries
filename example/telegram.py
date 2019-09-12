"""
порт десереализатора Телеграм для ЯП Python
"""
import io
import struct
import base64
import inspect
import datetime

from map import Map


class TeleData(object):
    USER_FLAG_ACCESS_HASH = 0x00000001
    USER_FLAG_FIRST_NAME = 0x00000002
    USER_FLAG_LAST_NAME = 0x00000004
    USER_FLAG_USERNAME = 0x00000008
    USER_FLAG_PHONE = 0x00000010
    USER_FLAG_PHOTO = 0x00000020
    USER_FLAG_STATUS = 0x00000040
    USER_FLAG_UNUSED = 0x00000080
    USER_FLAG_UNUSED2 = 0x00000100
    USER_FLAG_UNUSED3 = 0x00000200
    USER_FLAG_SELF = 0x00000400
    USER_FLAG_CONTACT = 0x00000800
    USER_FLAG_MUTUAL_CONTACT = 0x00001000
    USER_FLAG_DELETED = 0x00002000
    USER_FLAG_BOT = 0x00004000
    USER_FLAG_BOT_READING_HISTORY = 0x00008000
    USER_FLAG_BOT_CANT_JOIN_GROUP = 0x00010000
    USER_FLAG_VERIFIED = 0x00020000
    CHAT_FLAG_CREATOR = 0x00000001
    CHAT_FLAG_USER_KICKED = 0x00000002
    CHAT_FLAG_USER_LEFT = 0x00000004
    CHAT_FLAG_USER_IS_EDITOR = 0x00000008
    CHAT_FLAG_USER_IS_MODERATOR = 0x00000010
    CHAT_FLAG_IS_BROADCAST = 0x00000020
    CHAT_FLAG_IS_PUBLIC = 0x00000040
    CHAT_FLAG_IS_VERIFIED = 0x00000080
    MESSAGE_FLAG_UNREAD = 0x00000001
    MESSAGE_FLAG_OUT = 0x00000002
    MESSAGE_FLAG_FWD = 0x00000004
    MESSAGE_FLAG_REPLY = 0x00000008
    MESSAGE_FLAG_MENTION = 0x00000010
    MESSAGE_FLAG_CONTENT_UNREAD = 0x00000020
    MESSAGE_FLAG_HAS_MARKUP = 0x00000040
    MESSAGE_FLAG_HAS_ENTITIES = 0x00000080
    MESSAGE_FLAG_HAS_FROM_ID = 0x00000100
    MESSAGE_FLAG_HAS_MEDIA = 0x00000200
    MESSAGE_FLAG_HAS_VIEWS = 0x00000400
    MESSAGE_FLAG_HAS_BOT_ID = 0x00000800
    MESSAGE_FLAG_EDITED = 0x00008000
    MESSAGE_FLAG_MEGAGROUP = 0x80000000
    LAYER = 70

    # constructors: https://core.telegram.org/schema/json, https://core.telegram.org/schema
    # assert type 1: assert (constructor == ...
    # assert type 2: assert (result is not None)
    # assert type 3L assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])

    def __init__(self, cell):
        self.stream = io.BytesIO(cell)
        self.instances = list()

    def value_on_exception(return_value=int()):
        def wrap(func):
            def wrapper(self):
                try:
                    return func(self)
                except Exception as e:
                    return return_value
            return wrapper
        return wrap

    @property
    @value_on_exception()
    def get_int_byte(self):
        return ord(struct.unpack('c', self.stream.read(1))[0])

    @property
    @value_on_exception()
    def read_int32(self):
        return struct.unpack('<I', self.stream.read(4))[0]

    @property
    @value_on_exception()
    def read_int64(self):
        return struct.unpack('<Q', self.stream.read(8))[0]

    @property
    @value_on_exception()
    def read_double(self):
        return struct.unpack('d', struct.pack('Q', self.read_int64))[0]

    @property
    @value_on_exception(bytes())
    def read_bytes(self):
        sl = 1
        l = self.get_int_byte
        if l >= 254:
            l = self.get_int_byte | self.get_int_byte << 8 | self.get_int_byte << 16
            sl = 4
        string = struct.unpack('{}s'.format(l), self.stream.read(l))[0]
        i = sl
        while (l + i) % 4 != 0:
            c = self.get_int_byte
            i += 1
        # FIXME return string OR str(base64.b64encode(string)) OR string.decode('unicode_escape') for json-able
        return base64.b64encode(string).decode()

    @property
    @value_on_exception(str())
    def read_string(self):
        sl = 1
        l = self.get_int_byte
        if l >= 254:
            l = self.get_int_byte | self.get_int_byte << 8 | self.get_int_byte << 16
            sl = 4
        string = struct.unpack('{}s'.format(l), self.stream.read(l))[0]
        i = sl
        while (l + i) % 4 != 0:
            c = self.get_int_byte
            i += 1
        try:
            string = string.decode()
        except UnicodeDecodeError:
            string = string.decode('unicode_escape')

        return string

    @property
    @value_on_exception(bool())
    def read_bool(self):
        constructor = self.read_int32

        if constructor == 0x997275b5:
            return True
        elif constructor == 0xbc799737:
            return False

        return False

    @staticmethod
    def time_from_ts(ts):
        try:
            result = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
        except OSError:
            result = ts
        return result

    ######################################################

    def _tl_peerUser(self):
        constructor = 0x9db1bc6d
        self.instances.append(inspect.stack()[0][3])
        params = Map()
        if self.stream.tell() == len(self.stream.getvalue()):
            return params
        params.user_id = self.read_int32
        return params

    def _tl_peerChannel(self):
        constructor = 0xbddde532
        params = Map()
        params.channel_id = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_peerChat(self):
        constructor = 0xbad0e5bb
        params = Map()
        params.chat_id = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def peer_deserialize(self, constructor):
        result = None
        if constructor == 0x9db1bc6d:
            result = self._tl_peerUser()
        elif constructor == 0xbddde532:
            result = self._tl_peerChannel()
        elif constructor == 0xbad0e5bb:
            result = self._tl_peerChat()
        assert (result is not None), "constructor hex={0}, int={1} not defined".format(hex(constructor), constructor)
        return result

    def _tl_messageFwdHeader(self):
        constructor = 0xec338270
        params = Map()
        flags = self.read_int32
        params.flags = flags
        if (flags & 1) != 0:
            params.from_id = self.read_int32
        if (flags & 32) != 0:
            params.from_name = self.read_string
        date = self.read_int32
        params.date = self.time_from_ts(date)
        if (flags & 2) != 0:
            params.channel_id = self.read_int32
        if (flags & 4) != 0:
            params.channel_post = self.read_int32
        if (flags & 8) != 0:
            params.post_author = self.read_int32
        if (flags & 16) != 0:
            params.saved_from_peer = self.peer_deserialize(constructor)
        if (flags & 16) != 0:
            params.saved_from_msg_id = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageFwdHeader_layer96(self):
        constructor = 0x559ebe6d
        params = Map()
        flags = self.read_int32
        params.flags = flags
        if (flags & 1) != 0:
            params.from_id = self.read_int32
        date = self.read_int32
        params.date = self.time_from_ts(date)
        if (flags & 2) != 0:
            params.channel_id = self.read_int32
        if (flags & 4) != 0:
            params.channel_post = self.read_int32
        if (flags & 8) != 0:
            params.post_author = self.read_int32
        if (flags & 16) != 0:
            params.saved_from_peer = self.peer_deserialize(constructor)
        if (flags & 16) != 0:
            params.saved_from_msg_id = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageFwdHeader_layer72(self):
        constructor = 0xfadff4ac
        params = Map()
        flags = self.read_int32
        params.flags = flags
        if (flags & 1) != 0:
            params.from_id = self.read_int32
        date = self.read_int32
        params.date = self.time_from_ts(date)
        if (flags & 2) != 0:
            params.channel_id = self.read_int32
        if (flags & 4) != 0:
            params.channel_post = self.read_int32
        if (flags & 8) != 0:
            params.post_author = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageFwdHeader_layer68(self):
        constructor = 0xc786ddcb
        params = Map()
        flags = self.read_int32
        params.flags = flags
        if (flags & 1) != 0:
            params.from_id = self.read_int32
        date = self.read_int32
        params.date = self.time_from_ts(date)
        if (flags & 2) != 0:
            params.channel_id = self.read_int32
        if (flags & 4) != 0:
            params.channel_post = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def message_fwd_header_deserialize(self, constructor):
        result = None
        if constructor == 0xfadff4ac:
            result = self._tl_messageFwdHeader_layer72()
        elif constructor == 0xec338270:
            result = self._tl_messageFwdHeader()
        elif constructor == 0x559ebe6d:
            result = self._tl_messageFwdHeader_layer96()
        elif constructor == 0xc786ddcb:
            result = self._tl_messageFwdHeader_layer68()
        assert (result is not None), "constructor hex={0}, int={1} not defined".format(hex(constructor), constructor)
        return result

    def _tl_fileLocation_layer97(self):
        constructor = 0x91d11eb
        params = Map()
        params.dc_id = self.read_int32
        params.volume_id = self.read_int64
        params.local_id = self.read_int32
        params.secret = self.read_int64
        params.file_reference = self.read_bytes
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_fileLocation_layer82(self):
        constructor = 0x53d69076
        params = Map()
        params.dc_id = self.read_int32
        params.volume_id = self.read_int64
        params.local_id = self.read_int32
        params.secret = self.read_int64
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_fileEncryptedLocation(self):
        constructor = 0x55555554
        params = Map()
        params.dc_id = self.read_int32
        params.volume_id = self.read_int64
        params.local_id = self.read_int32
        params.secret = self.read_int64
        params.key = self.read_bytes
        params.iv = self.read_bytes
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_fileLocationUnavailable(self):
        constructor = 0x7c596b46
        params = Map()
        params.local_id = self.read_int32
        params.secret = self.read_int64
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_fileLocation_to_be_depreacted(self):
        constructor = 0xbc7fc6cd
        params = Map()
        params.volume_id = self.read_int64
        params.local_id = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def file_location_deserialize(self, constructor):
        result = None
        if constructor == 0x53d69076:
            result = self._tl_fileLocation_layer82()
        elif constructor == 0x55555554:
            result = self._tl_fileEncryptedLocation()
        elif constructor == 0x7c596b46:
            result = self._tl_fileLocationUnavailable()
        elif constructor == 0x91d11eb:
            result = self._tl_fileLocation_layer97()
        elif constructor == 0xbc7fc6cd:
            result = self._tl_fileLocation_to_be_depreacted()
        assert (result is not None), "constructor hex={0}, int={1} not defined".format(hex(constructor), constructor)
        return result

    def _tl_photoSize(self):
        constructor = 0x77bfb61b
        params = Map()
        params.type = self.read_string
        params.location = self.file_location_deserialize(self.read_int32)
        params.w = self.read_int32
        params.h = self.read_int32
        params.size = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_photoSizeEmpty(self):
        constructor = 0xe17e23c
        params = Map()
        # startReadPosiition = self.get_position()
        params.typeof = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_photoCachedSize(self):
        constructor = 0xe9a734fa
        params = Map()
        params.type = self.read_string
        params.location = self.file_location_deserialize(self.read_int32)
        params.w = self.read_int32
        params.h = self.read_int32
        params.bytes = self.read_bytes
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_photoStrippedSize(self):
        constructor = 0xe0b0bc2e
        params = Map()
        params.type = self.read_string
        params.bytes = self.read_bytes
        params.w = 50
        params.h = 50
        self.instances.append(inspect.stack()[0][3])
        return params

    def photo_size_deserialize(self, constructor):
        result = None
        if constructor == 0x77bfb61b:
            result = self._tl_photoSize()
        elif constructor == 0xe17e23c:
            result = self._tl_photoSizeEmpty()
        elif constructor == 0xe9a734fa:
            result = self._tl_photoCachedSize()
        elif constructor == 0xe0b0bc2e:
            result = self._tl_photoStrippedSize()
        assert (result is not None), "constructor hex={0}, int={1} not defined".format(hex(constructor), constructor)
        return result

    def _tl_photo(self):
        constructor = 0xd07504a5
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.has_stickers = (flags & 1) != 0
        params.id = self.read_int64
        params.access_hash = self.read_int64
        params.file_reference = self.read_bytes
        date = self.read_int32
        params.date = self.time_from_ts(date)
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        sizes = list()
        for i in range(0, count):
            obj = self.photo_size_deserialize(self.read_int32)
            if obj is None:  # is None по какой-то причине плох в этом месте
                return
            sizes.append(obj)
        params.sizes = sizes
        params.dc_id = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_photo_layer97(self):
        constructor = 0x9c477dd8
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.has_stickers = (flags & 1) != 0
        params.id = self.read_int64
        params.access_hash = self.read_int64
        params.file_reference = self.read_bytes
        date = self.read_int32
        params.date = self.time_from_ts(date)
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        sizes = list()
        for i in range(0, count):
            obj = self.photo_size_deserialize(self.read_int32)
            if obj is None:  # is None по какой-то причине плох в этом месте
                return
            sizes.append(obj)
        params.sizes = sizes
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_photo_layer82(self):
        constructor = 0x9288dd29
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.has_stickers = (flags & 1) != 0
        params.id = self.read_int64
        params.access_hash = self.read_int64
        date = self.read_int32
        params.date = self.time_from_ts(date)
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        sizes = list()
        for i in range(0, count):
            obj = self.photo_size_deserialize(self.read_int32)
            if obj is None:  # is None по какой-то причине плох в этом месте
                return
            sizes.append(obj)
        params.sizes = sizes
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_geoPointEmpty(self):
        constructor = 0x1117dd5f
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_geoPoint(self):
        constructor = 0x2049d70c
        params = Map()
        params._long = self.read_double
        params.lat = self.read_double
        self.instances.append(inspect.stack()[0][3])
        return params

    def geo_point_deserialize(self, constructor):
        result = None
        if constructor == 0x1117dd5f:
            result = self._tl_geoPointEmpty()
        elif constructor == 0x2049d70c:
            result = self._tl_geoPoint()
        assert (result is not None), "constructor hex={0}, int={1} not defined".format(hex(constructor), constructor)
        return result

    def _tl_photo_old(self):
        constructor = 0x22b56751
        params = Map()
        params.id = self.read_int64
        params.access_hash = self.read_int64
        params.user_id = self.read_int32
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.caption = self.read_string
        params.geo = self.geo_point_deserialize(self.read_int32)
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        sizes = list()
        for i in range(0, count):
            obj = self.photo_size_deserialize(self.read_int32)
            if obj is None:
                return
            sizes.append(obj)
        params.sizes = sizes
        return params

    def _tl_photo_old2(self):
        constructor = 0xc3838076
        params = Map()
        params.id = self.read_int64
        params.access_hash = self.read_int64
        params.user_id = self.read_int32
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.geo = self.geo_point_deserialize(self.read_int32)
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        sizes = list()
        for i in range(0, count):
            obj = self.photo_size_deserialize(self.read_int32)
            if obj is None:
                return
            sizes.append(obj)
        params.sizes = sizes
        return params

    def _tl_photo_layer55(self):
        constructor = 0xcded42fe
        params = Map()
        params.id = self.read_int64
        params.access_hash = self.read_int64
        date = self.read_int32
        params.date = self.time_from_ts(date)
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        sizes = list()
        for i in range(0, count):
            obj = self.photo_size_deserialize(self.read_int32)
            if obj is None:
                return
            sizes.append(obj)
        params.sizes = sizes
        return params

    def photo_deserialize(self, constructor):
        result = None
        if constructor == 0x22b56751:
            result = self._tl_photo_old()
        elif constructor == 0xd07504a5:
            result = self._tl_photo()
        elif constructor == 0x9c477dd8:
            result = self._tl_photo_layer97()
        elif constructor == 0x9288dd29:
            result = self._tl_photo_layer82()
        elif constructor == 0xc3838076:
            result = self._tl_photo_old2()
        elif constructor == 0xcded42fe:
            result = self._tl_photo_layer55()
        elif constructor == 0x2331b22d:
            result = self._tl_photoEmpty()
        assert (result is not None), "constructor hex={0}, int={1} not defined".format(hex(constructor), constructor)
        return result

    def page_caption_deserialize(self, constructor):
        assert (constructor == 0x6f747657), "{} asseratation".format(inspect.stack()[0][3])
        params = Map()
        params.text = self.rich_text_deserialize(self.read_int32)
        params.credit = self.rich_text_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_pageBlockTitle(self):
        constructor = 0x70abc3fd
        params = Map()
        params.text = self.rich_text_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_pageBlockAuthorDate(self):
        constructor = 0xbaafe5e0
        params = Map()
        params.author = self.rich_text_deserialize(self.read_int32)
        published_date = self.read_int32
        params.published_date = self.time_from_ts(published_date)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_pageBlockParagraph(self):
        constructor = 0x467a0766
        params = Map()
        params.text = self.rich_text_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_pageBlockAnchor(self):
        constructor = 0xce0d37b0
        params = Map()
        params.name = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_pageBlockHeader(self):
        constructor = 0xbfd064ec
        params = Map()
        params.text = self.rich_text_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_pageBlockList(self):
        constructor = 0x3a58c7f4
        params = Map()
        params.ordered = self.read_bool
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        elements = list()
        for i in range(0, count):
            obj = self.rich_text_deserialize(self.read_int32)
            if obj is None:
                return
            elements.append(obj)
        params.elements = elements
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_pageBlockPhoto(self):
        constructor = 0x1759c560
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.photo_id = self.read_int64
        params.caption = self.page_caption_deserialize(self.read_int32)
        if (flags & 1) != 0:
            params.url = self.read_string
        if (flags & 1) != 0:
            params.webpage_id = self.read_int64
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_pageBlockDivider(self):
        constructor = 0xdb20b188
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_pageBlockSubheader(self):
        constructor = 0xf12bb6e1
        params = Map()
        params.text = self.rich_text_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_pageBlockBlockquote(self):
        constructor = 0x263d7c26
        params = Map()
        params.text = self.rich_text_deserialize(self.read_int32)
        params.caption = self.rich_text_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_pageBlockVideo(self):
        constructor = 0x7c8fe7b6
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.autoplay = (flags & 1) != 0
        params.loop = (flags & 2) != 0
        params.video_id = self.read_int64
        params.caption = self.page_caption_deserialize(self.read_int32)

        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_pageBlockVideo_layer82(self):
        constructor = 0xd9d71866
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.autoplay = (flags & 1) != 0
        params.loop = (flags & 2) != 0
        params.video_id = self.read_int64
        params.caption = self.rich_text_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_pageBlockPreformatted(self):
        constructor = 0xc070d93e
        params = Map()
        params.text = self.rich_text_deserialize(self.read_int32)
        params.language = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_pageBlockEmbed(self):
        constructor = 0xcde200d1
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.full_width = (flags & 1) != 0
        params.allow_scrolling = (flags & 8) != 0
        if (flags & 2) != 0:
            params.url = self.read_string
        if (flags & 4) != 0:
            params.html = self.read_string
        if (flags & 16) != 0:
            params.poster_photo_id = self.read_int64
        params.w = self.read_int32
        params.h = self.read_int32
        params.caption = self.rich_text_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_pageBlockUnsupported(self):
        constructor = 0x13567e8a
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_pageBlockAuthorDate_layer60(self):
        constructor = 0x3d5b64f2
        params = Map()
        authorString = self.read_string
        params.author = self._tl_textPlain()
        params.author.text = authorString
        published_date = self.read_int32
        params.published_date = self.time_from_ts(published_date)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_pageBlockCollage(self):
        constructor = 0x8b31c4f
        params = Map()
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        elements = list()
        for i in range(0, count):
            obj = self.page_block_deserialize(self.read_int32)
            if obj is None:
                return
            elements.append(obj)
        params.elements = elements
        params.caption = self.rich_text_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_pageBlockFooter(self):
        constructor = 0x48870999
        params = Map()
        params.text = self.rich_text_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_pageBlockEmbed_layer60(self):
        constructor = 0xd935d8fb
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.full_width = (flags & 1) != 0
        params.allow_scrolling = (flags & 8) != 0
        if (flags & 2) != 0:
            params.url = self.read_string
        if (flags & 4) != 0:
            params.html = self.read_string
        params.w = self.read_int32
        params.h = self.read_int32
        params.caption = self.rich_text_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_pageBlockSubtitle(self):
        constructor = 0x8ffa9a1f
        params = Map()
        params.text = self.rich_text_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_pageBlockEmbedPost(self):
        constructor = 0x292c7be9
        params = Map()
        params.url = self.read_string
        params.webpage_id = self.read_int64
        params.author_photo_id = self.read_int64
        params.author = self.read_string
        date = self.read_int32
        params.date = self.time_from_ts(date)
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        blocks = list()
        for i in range(0, count):
            obj = self.page_block_deserialize(self.read_int32)
            if obj is None:
                blocks.append(obj)
        params.blocks = blocks
        params.caption = self.rich_text_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_chatPhotoEmpty(self):
        constructor = 0x37c1011c
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_chatPhoto(self):
        constructor = 0x475cdbd5
        params = Map()
        params.photo_small = self.file_location_deserialize(self.read_int32)
        params.photo_big = self.file_location_deserialize(self.read_int32)
        params.dc_id = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_chatPhoto_layer97(self):
        constructor = 0x6153276a
        params = Map()
        params.photo_small = self.file_location_deserialize(self.read_int32)
        params.photo_big = self.file_location_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def chat_photo_deserialize(self, constructor):
        result = None
        if constructor == 0x37c1011c:
            result = self._tl_chatPhotoEmpty()
        elif constructor == 0x6153276a:
            result = self._tl_chatPhoto_layer97()
        elif constructor == 0x475cdbd5:
            result = self._tl_chatPhoto()
        assert (result is not None), "constructor hex={0}, int={1} not defined".format(hex(constructor), constructor)
        return result

    def _tl_inputChannelEmpty(self):
        constructor = 0xee8c1e86
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_inputChannel(self):
        constructor = 0xafeb712e
        params = Map()
        params.channel_id = self.read_int32
        params.access_hash = self.read_int64
        self.instances.append(inspect.stack()[0][3])
        return params

    def input_channel_deserialize(self, constructor):
        result = None
        if constructor == 0xee8c1e86:
            result = self._tl_inputChannelEmpty()
        elif constructor == 0xafeb712e:
            result = self._tl_inputChannel()
        assert (result is not None), "constructor hex={0}, int={1} not defined".format(hex(constructor), constructor)
        return result

    def _tl_chat(self):
        constructor = 0x3bda1bde
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.creator = (flags & 1) != 0
        params.kicked = (flags & 2) != 0
        params.left = (flags & 4) != 0
        params.deactivated = (flags & 32) != 0
        params.id = self.read_int32
        params.title = self.read_string
        params.photo = self.chat_photo_deserialize(self.read_int32)
        params.participants_count = self.read_int32
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.version = self.read_int32
        if (flags & 64) != 0:
            params.migrated_to = self.input_channel_deserialize(self.read_int32)
        if (flags & 16384) != 0:
            params.admin_rights = self.chat_admin_rights_deserialize(self.read_int32)
        if (flags & 262144) != 0:
            params.default_banned_rights = self.chat_banned_rights_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_chat_layer92(self):
        constructor = 0xd91cdd54
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.creator = (flags & 1) != 0
        params.kicked = (flags & 2) != 0
        params.left = (flags & 4) != 0
        params.admins_enabled = (flags & 8) != 0
        params.admin = (flags & 16) != 0
        params.deactivated = (flags & 32) != 0
        params.id = self.read_int32
        params.title = self.read_string
        params.photo = self.chat_photo_deserialize(self.read_int32)
        params.participants_count = self.read_int32
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.version = self.read_int32
        if (flags & 64) != 0:
            params.migrated_to = self.input_channel_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_channelAdminRights(self):
        constructor = 0x5d7ceba5
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.change_info = (flags & 1) != 0
        params.post_messages = (flags & 2) != 0
        params.edit_messages = (flags & 4) != 0
        params.delete_messages = (flags & 8) != 0
        params.ban_users = (flags & 16) != 0
        params.invite_users = (flags & 32) != 0
        params.invite_link = (flags & 64) != 0
        params.pin_messages = (flags & 128) != 0
        params.add_admins = (flags & 512) != 0
        self.instances.append(inspect.stack()[0][3])
        return params

    def channel_admin_rights_deserialize(self, constructor):
        assert (constructor == 0x5d7ceba5), "{} asseratation".format(inspect.stack()[0][3])
        result = self._tl_channelAdminRights()
        self.instances.append(inspect.stack()[0][3])
        return result

    def _tl_channelBannedRights(self):
        constructor = 0x58cf4249
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.view_messages = (flags & 1) != 0
        params.send_messages = (flags & 2) != 0
        params.send_media = (flags & 4) != 0
        params.send_stickers = (flags & 8) != 0
        params.send_gifs = (flags & 16) != 0
        params.send_games = (flags & 32) != 0
        params.send_inline = (flags & 64) != 0
        params.embed_links = (flags & 128) != 0
        params.until_date = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def channel_banned_rights_deserialize(self, constructor):
        assert (constructor == 0x58cf4249), "{} asseratation".format(inspect.stack()[0][3])
        result = self._tl_channelBannedRights()
        self.instances.append(inspect.stack()[0][3])
        return result

    def _tl_channel_layer77(self):
        constructor = 0x450b7115
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.creator = (flags & 1) != 0
        params.left = (flags & 4) != 0
        params.broadcast = (flags & 32) != 0
        params.verified = (flags & 128) != 0
        params.megagroup = (flags & 256) != 0
        params.restricted = (flags & 512) != 0
        params.democracy = (flags & 1024) != 0
        params.signatures = (flags & 2048) != 0
        params.min = (flags & 4096) != 0
        params.id = self.read_int32
        if (flags & 8192) != 0:
            params.access_hash = self.read_int64
        params.title = self.read_string
        if (flags & 64) != 0:
            params.username = self.read_string
        params.photo = self.chat_photo_deserialize(self.read_int32)
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.version = self.read_int32
        if (flags & 512) != 0:
            params.restriction_reason = self.read_string
        if (flags & 16384) != 0:
            params.admin_rights = self.channel_admin_rights_deserialize(self.read_int32)
        if (flags & 32768) != 0:
            params.banned_rights = self.channel_banned_rights_deserialize(self.read_int32)
        if (flags & 131072) != 0:
            params.participants_count = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_chat_admin_rights(self):
        constructor = 0x5fb224d5
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.change_info = (flags & 1) != 0
        params.post_messages = (flags & 2) != 0
        params.edit_messages = (flags & 4) != 0
        params.delete_messages = (flags & 8) != 0
        params.ban_users = (flags & 16) != 0
        params.invite_users = (flags & 32) != 0
        params.pin_messages = (flags & 128) != 0
        params.add_admins = (flags & 512) != 0
        self.instances.append(inspect.stack()[0][3])
        return params

    def chat_banned_rights(self):
        constructor = 0x9f120418
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.view_messages = (flags & 1) != 0
        params.send_messages = (flags & 2) != 0
        params.send_media = (flags & 4) != 0
        params.send_stickers = (flags & 8) != 0
        params.send_gifs = (flags & 16) != 0
        params.send_games = (flags & 32) != 0
        params.send_inline = (flags & 64) != 0
        params.embed_links = (flags & 128) != 0
        params.send_polls = (flags & 256) != 0
        params.change_info = (flags & 1024) != 0
        params.invite_users = (flags & 32768) != 0
        params.pin_messages = (flags & 131072) != 0
        until_date = self.read_int64
        params.until_date = self.time_from_ts(until_date)
        self.instances.append(inspect.stack()[0][3])
        return params

    def chat_admin_rights_deserialize(self, constructor):
        assert (constructor == 0x5fb224d5), "{} asseratation".format(inspect.stack()[0][3])
        result = self._tl_chat_admin_rights()
        self.instances.append(inspect.stack()[0][3])
        return result

    def chat_banned_rights_deserialize(self, constructor):
        assert (constructor == 0x9f120418), "{} asseratation".format(inspect.stack()[0][3])
        result = self.chat_banned_rights()
        self.instances.append(inspect.stack()[0][3])
        return result

    def _tl_channel(self):
        constructor = 0x4df30834
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.creator = (flags & 1) != 0
        params.left = (flags & 4) != 0
        params.broadcast = (flags & 32) != 0
        params.verified = (flags & 128) != 0
        params.megagroup = (flags & 256) != 0
        params.restricted = (flags & 512) != 0
        params.signatures = (flags & 2048) != 0
        params.min = (flags & 4096) != 0
        params.scam = (flags & 524288) != 0
        params.has_link = (flags & 1048576) != 0
        params.id = self.read_int32
        if (flags & 8192) != 0:
            params.access_hash = self.read_int64
        params.title = self.read_string
        if (flags & 64) != 0:
            params.username = self.read_string
        params.photo = self.chat_photo_deserialize(self.read_int32)
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.version = self.read_int32
        if (flags & 512) != 0:
            params.restriction_reason = self.read_string
        if (flags & 16384) != 0:
            params.admin_rights = self.chat_admin_rights_deserialize(self.read_int32)
        if (flags & 32768) != 0:
            params.banned_rights = self.chat_banned_rights_deserialize(self.read_int32)
        if (flags & 262144) != 0:
            params.default_banned_rights = self.chat_banned_rights_deserialize(self.read_int32)
        if (flags & 131072) != 0:
            params.participants_count = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_channel_layer92(self):
        constructor = 0xc88974ac
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.creator = (flags & 1) != 0
        params.left = (flags & 4) != 0
        params.editor = (flags & 8) != 0
        params.broadcast = (flags & 32) != 0
        params.verified = (flags & 128) != 0
        params.megagroup = (flags & 256) != 0
        params.restricted = (flags & 512) != 0
        params.democracy = (flags & 1024) != 0
        params.signatures = (flags & 2048) != 0
        params.min = (flags & 4096) != 0
        params.id = self.read_int32
        if (flags & 8192) != 0:
            params.access_hash = self.read_int64
        params.title = self.read_string
        if (flags & 64) != 0:
            params.username = self.read_string
        params.photo = self.chat_photo_deserialize(self.read_int32)
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.version = self.read_int32
        if (flags & 512) != 0:
            params.restriction_reason = self.read_string
        if (flags & 16384) != 0:
            params.admin_rights = self.channel_admin_rights_deserialize(self.read_int32)
        if (flags & 32768) != 0:
            params.banned_rights = self.channel_banned_rights_deserialize(self.read_int32)
        if (flags & 131072) != 0:
            params.participants_count = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_channel_layer72(self):
        constructor = 0xcb44b1c
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.creator = (flags & 1) != 0
        params.left = (flags & 4) != 0
        params.broadcast = (flags & 32) != 0
        params.verified = (flags & 128) != 0
        params.megagroup = (flags & 256) != 0
        params.restricted = (flags & 512) != 0
        params.democracy = (flags & 1024) != 0
        params.signatures = (flags & 2048) != 0
        params.min = (flags & 4096) != 0
        params.id = self.read_int32
        if (flags & 8192) != 0:
            params.access_hash = self.read_int64
        params.title = self.read_string
        if (flags & 64) != 0:
            params.username = self.read_string
        params.photo = self.chat_photo_deserialize(self.read_int32)
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.version = self.read_int32
        if (flags & 512) != 0:
            params.restriction_reason = self.read_string
        if (flags & 16384) != 0:
            params.admin_rights = self.channel_admin_rights_deserialize(self.read_int32)
        if (flags & 32768) != 0:
            params.banned_rights = self.channel_banned_rights_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_chatEmpty(self):
        constructor = 0x9ba2d800
        params = Map()
        params.id = self.read_int32
        params.title = "DELETED"
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_chat_old(self):
        constructor = 0x6e9c9bc7
        params = Map()
        params.id = self.read_int32
        params.title = self.read_string
        params.photo = self.chat_photo_deserialize(self.read_int32)
        params.participants_count = self.read_int32
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.left = self.read_bool
        params.version = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_channel_old(self):
        constructor = 0x678e9587
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.creator = (flags & 1) != 0
        params.kicked = (flags & 2) != 0
        params.left = (flags & 4) != 0
        params.moderator = (flags & 16) != 0
        params.broadcast = (flags & 32) != 0
        params.verified = (flags & 128) != 0
        params.megagroup = (flags & 256) != 0
        params.explicit_content = (flags & 512) != 0
        params.id = self.read_int32
        params.access_hash = self.read_int64
        params.title = self.read_string
        if (flags & 64) != 0:
            params.username = self.read_string
        params.photo = self.chat_photo_deserialize(self.read_int32)
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.version = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_pageBlockChannel(self):
        constructor = 0xef1751b5
        params = Map()
        params.channel = self.chat_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_pageBlockSlideshow(self):
        constructor = 0x130c8963
        params = Map()
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        elements = list()
        for i in range(0, count):
            obj = self.page_block_deserialize(self.read_int32)
            if obj is None:
                return
            elements.append(obj)
        params.elements = elements
        params.caption = self.rich_text_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_pageBlockPullquote(self):
        constructor = 0x4f4456d3
        params = Map()
        params.text = self.rich_text_deserialize(self.read_int32)
        params.caption = self.rich_text_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_pageBlockAudio(self):
        constructor = 0x31b81a7f
        params = Map()
        params.audio_id = self.read_int64
        params.caption = self.rich_text_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_pageRelatedArticle(self):
        constructor = 0xb390dc08
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.url = self.read_string
        params.webpage_id = self.read_int64
        if (flags & 1) != 0:
            params.title = self.read_string
        if (flags & 2) != 0:
            params.description = self.read_string
        if (flags & 4) != 0:
            params.photo_id = self.read_int64
        if (flags & 8) != 0:
            params.author = self.read_string
        if (flags & 16) != 0:
            params.published_date = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def page_related_article_deserialize(self, constructor):
        assert (constructor == 0xb390dc08), "{} asseratation".format(inspect.stack()[0][3])
        result = self._tl_pageRelatedArticle()
        self.instances.append(inspect.stack()[0][3])
        return result

    def _tl_pageBlockRlatedArticles(self):
        constructor = 0x16115a96
        params = Map()
        params.title = self.rich_text_deserialize(self.read_int32)
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        elements = list()
        for i in range(0, count):
            obj = self.page_related_article_deserialize(self.read_int32)
            if obj is None:
                return
            elements.append(obj)
        params.elements = elements
        self.instances.append(inspect.stack()[0][3])
        return params

    def page_block_deserialize(self, constructor):
        result = None
        if constructor == 0xdb20b188:
            result = self._tl_pageBlockDivider()
        elif constructor == 0x1759c560:
            result = self._tl_pageBlockPhoto()
        elif constructor == 0x16115a96:
            result = self._tl_pageBlockRlatedArticles()
        elif constructor == 0xbaafe5e0:
            result = self._tl_pageBlockAuthorDate()
        elif constructor == 0xc070d93e:
            result = self._tl_pageBlockPreformatted()
        elif constructor == 0xcde200d1:
            result = self._tl_pageBlockEmbed()
        elif constructor == 0xce0d37b0:
            result = self._tl_pageBlockAnchor()
        elif constructor == 0xbfd064ec:
            result = self._tl_pageBlockHeader()
        elif constructor == 0xd9d71866:
            result = self._tl_pageBlockVideo_layer82()
        elif constructor == 0x7c8fe7b6:
            result = self._tl_pageBlockVideo()
        elif constructor == 0x13567e8a:
            result = self._tl_pageBlockUnsupported()
        elif constructor == 0x467a0766:
            result = self._tl_pageBlockParagraph()
        elif constructor == 0x3d5b64f2:
            result = self._tl_pageBlockAuthorDate_layer60()
        elif constructor == 0x8b31c4f:
            result = self._tl_pageBlockCollage()
        elif constructor == 0x48870999:
            result = self._tl_pageBlockFooter()
        elif constructor == 0x3a58c7f4:
            result = self._tl_pageBlockList()
        elif constructor == 0xd935d8fb:
            result = self._tl_pageBlockEmbed_layer60()
        elif constructor == 0xe9c69982:
            result = self._tl_pageBlockPhoto_layer82()
        elif constructor == 0x8ffa9a1f:
            result = self._tl_pageBlockSubtitle()
        elif constructor == 0x263d7c26:
            result = self._tl_pageBlockBlockquote()
        elif constructor == 0x292c7be9:
            result = self._tl_pageBlockEmbedPost()
        elif constructor == 0x70abc3fd:
            result = self._tl_pageBlockTitle()
        elif constructor == 0xef1751b5:
            result = self._tl_pageBlockChannel()
        elif constructor == 0x39f23300:
            result = self._tl_pageBlockCover()
        elif constructor == 0xf12bb6e1:
            result = self._tl_pageBlockSubheader()
        elif constructor == 0x130c8963:
            result = self._tl_pageBlockSlideshow()
        elif constructor == 0x4f4456d3:
            result = self._tl_pageBlockPullquote()
        elif constructor == 0x31b81a7f:
            result = self._tl_pageBlockAudio()
        assert (result is not None), "constructor hex={0}, int={1} not defined".format(hex(constructor), constructor)
        return result

    def _tl_pageBlockCover(self):
        constructor = 0x39f23300
        params = Map()
        params.cover = self.page_block_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_textEmpty(self):
        constructor = 0xdc3d824f
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_textPlain(self):
        constructor = 0x744694e0
        params = Map()
        params.text = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_textConcat(self):
        constructor = 0x7e6260d7
        params = Map()
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        texts = list()
        for i in range(0, count):
            obj = self.rich_text_deserialize(self.read_int32)
            if obj is None:
                return
            texts.append(obj)
        params.texts = texts
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_textBold(self):
        constructor = 0x6724abc4
        params = Map()
        params.text = self.rich_text_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_textUrl(self):
        constructor = 0x3c2884c1
        params = Map()
        params.text = self.rich_text_deserialize(self.read_int32)
        params.url = self.read_string
        params.webpage_id = self.read_int64
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_textItalic(self):
        constructor = 0xd912a59c
        params = Map()
        params.text = self.rich_text_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_textStrike(self):
        constructor = 0x9bf8bb95
        params = Map()
        params.text = self.rich_text_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_textFixed(self):
        constructor = 0x6c3f19b9
        params = Map()
        params.text = self.rich_text_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_textEmail(self):
        constructor = 0xde5a0dd6
        params = Map()
        params.text = self.rich_text_deserialize(self.read_int32)
        params.email = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_textUnderline(self):
        constructor = 0xc12622c4
        params = Map()
        params.text = self.rich_text_deserialize(self.read_int32)
        params.email = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def rich_text_deserialize(self, constructor):
        result = None
        if constructor == 0xdc3d824f:
            result = self._tl_textEmpty()
        elif constructor == 0x3c2884c1:
            result = self._tl_textUrl()
        elif constructor == 0x9bf8bb95:
            result = self._tl_textStrike()
        elif constructor == 0x6c3f19b9:
            result = self._tl_textFixed()
        elif constructor == 0xde5a0dd6:
            result = self._tl_textEmail()
        elif constructor == 0x744694e0:
            result = self._tl_textPlain()
        elif constructor == 0x7e6260d7:
            result = self._tl_textConcat()
        elif constructor == 0x6724abc4:
            result = self._tl_textBold()
        elif constructor == 0xd912a59c:
            result = self._tl_textItalic()
        elif constructor == 0xc12622c4:
            result = self._tl_textUnderline()
        assert (result is not None), "constructor hex={0}, int={1} not defined".format(hex(constructor), constructor)
        return result

    def _tl_pageBlockPhoto_layer82(self):
        constructor = 0xe9c69982
        params = Map()
        params.photo_id = self.read_int64
        params.caption = self.rich_text_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_pageFullPart(self):
        # My method
        params = Map()
        blocks = list()
        photos = list()
        documents = list()
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        for i in range(0, count):
            obj = self.page_block_deserialize(self.read_int32)
            if obj is None:
                return
            blocks.append(obj)
        params.blocks = blocks
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        for i in range(0, count):
            obj = self.photo_deserialize(self.read_int32)
            if obj is None:
                return
            photos.append(obj)
        params.photos = photos
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        for i in range(0, count):
            obj = self.document_deserialize(self.read_int32)
            if obj is None:
                return
            documents.append(obj)
        params.documents = documents
        return params

    def _tl_pageFull_layer67(self):
        constructor = 0xd7a19d69
        params = self._tl_pageFullPart()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_pageFull_layer82(self):
        constructor = 0x556ec7aa
        params = self._tl_pageFullPart()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_pagePart_layer67(self):
        constructor = 0x8dee6c44
        params = self._tl_pageFullPart()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_pagePart_layer82(self):
        constructor = 0x8e3f9ebe
        params = self._tl_pageFullPart()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_page(self):
        constructor = 0xae891bec
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.part = (flags & 1) != 0
        params.rtl = (flags & 2) != 0
        params.url = self.read_string

        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        blocks = list()
        for i in range(0, count):
            obj = self.page_block_deserialize(self.read_int32)
            if obj is None:
                return
            blocks.append(obj)
        params.blocks = blocks

        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        photos = list()
        for i in range(0, count):
            obj = self.photo_deserialize(self.read_int32)
            if obj is None:
                return
            photos.append(obj)
        params.photos = photos

        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        documents = list()
        for i in range(0, count):
            obj = self.document_deserialize(self.read_int32)
            if obj is None:
                return
            documents.append(obj)
        params.documents = documents

        self.instances.append(inspect.stack()[0][3])
        return params

    def page_deserialize(self, constructor):
        result = None
        if constructor == 0x556ec7aa:
            result = self._tl_pageFull_layer82()
        elif constructor == 0x8dee6c44:
            result = self._tl_pagePart_layer67()
        elif constructor == 0xd7a19d69:
            result = self._tl_pageFull_layer67()
        elif constructor == 0x8e3f9ebe:
            result = self._tl_pagePart_layer82()
        elif constructor == 0xae891bec:
            result = self._tl_page()
        assert (result is not None), "constructor hex={0}, int={1} not defined".format(hex(constructor), constructor)
        return result

    def _tl_webPage(self):
        constructor = 0x5f07b4bc
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.id = self.read_int64
        params.url = self.read_string
        params.display_url = self.read_string
        params.hash = self.read_int32
        if (flags & 1) != 0:
            params.typeof = self.read_string
        if (flags & 2) != 0:
            params.site_name = self.read_string
        if (flags & 4) != 0:
            params.title = self.read_string
        if (flags & 8) != 0:
            params.description = self.read_string
        if (flags & 16) != 0:
            params.photo = self.photo_deserialize(self.read_int32)
        if (flags & 32) != 0:
            params.embed_url = self.read_string
        if (flags & 32) != 0:
            params.embed_type = self.read_string
        if (flags & 64) != 0:
            params.embed_width = self.read_int32
        if (flags & 64) != 0:
            params.embed_height = self.read_int32
        if (flags & 128) != 0:
            params.duration = self.read_int32
        if (flags & 256) != 0:
            params.author = self.read_string
        if (flags & 512) != 0:
            params.document = self.document_deserialize(self.read_int32)
        if (flags & 1024) != 0:
            params.cached_page = self.page_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_webPageEmpty(self):
        constructor = 0xeb1477e8
        params = Map()
        params.id = self.read_int64
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_webPage_old(self):
        constructor = 0xa31ea0b5
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.id = self.read_int64
        params.url = self.read_string
        params.display_url = self.read_string
        if (flags & 1) != 0:
            params.type = self.read_string
        if (flags & 2) != 0:
            params.site_name = self.read_string
        if (flags & 4) != 0:
            params.title = self.read_string
        if (flags & 8) != 0:
            params.description = self.read_string
        if (flags & 16) != 0:
            params.photo = self.photo_deserialize(self.read_int32)
        if (flags & 32) != 0:
            params.embed_url = self.read_string
        if (flags & 32) != 0:
            params.embed_type = self.read_string
        if (flags & 64) != 0:
            params.embed_width = self.read_int32
        if (flags & 64) != 0:
            params.embed_height = self.read_int32
        if (flags & 128) != 0:
            params.duration = self.read_int32
        if (flags & 256) != 0:
            params.author = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_webPage_layer58(self):
        constructor = 0xca820ed7
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.id = self.read_int64
        params.url = self.read_string
        params.display_url = self.read_string
        if (flags & 1) != 0:
            params.type = self.read_string
        if (flags & 2) != 0:
            params.site_name = self.read_string
        if (flags & 4) != 0:
            params.title = self.read_string
        if (flags & 8) != 0:
            params.description = self.read_string
        if (flags & 16) != 0:
            params.photo = self.photo_deserialize(self.read_int32)
        if (flags & 32) != 0:
            params.embed_url = self.read_string
        if (flags & 32) != 0:
            params.embed_type = self.read_string
        if (flags & 64) != 0:
            params.embed_width = self.read_int32
        if (flags & 64) != 0:
            params.embed_height = self.read_int32
        if (flags & 128) != 0:
            params.duration = self.read_int32
        if (flags & 256) != 0:
            params.author = self.read_string
        if (flags & 512) != 0:
            params.document = self.document_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_webPageUrlPending(self):
        constructor = 0xd41a5167
        params = Map()
        params.url = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_webPagePending(self):
        constructor = 0xc586da1c
        params = Map()
        params.id = self.read_int64
        date = self.read_int32
        params.date = self.time_from_ts(date)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_webPageNotModified(self):
        constructor = 0x85849473
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def web_page_deserialize(self, constructor):
        result = None
        if constructor == 0x5f07b4bc:
            result = self._tl_webPage()
        elif constructor == 0xa31ea0b5:
            result = self._tl_webPage_old()
        elif constructor == 0xd41a5167:
            result = self._tl_webPageUrlPending()
        elif constructor == 0xc586da1c:
            result = self._tl_webPagePending()
        elif constructor == 0xeb1477e8:
            result = self._tl_webPageEmpty()
        elif constructor == 0xca820ed7:
            result = self._tl_webPage_layer58()
        elif constructor == 0x85849473:
            result = self._tl_webPageNotModified()
        assert (result is not None), "constructor hex={0}, int={1} not defined".format(hex(constructor), constructor)
        return result

    def _tl_messageMediaWebPage(self):
        constructor = 0xa32dd600
        params = Map()
        params.webpage = self.web_page_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_documentAttributeAudio(self):
        constructor = 0x9852f9c6
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.voice = (flags & 1024) != 0
        params.duration = self.read_int32
        if (flags & 1) != 0:
            params.title = self.read_string
        if (flags & 2) != 0:
            params.performer = self.read_string
        if (flags & 4) != 0:
            params.waveform = self.read_bytes
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_documentAttributeVideo(self):
        constructor = 0xef02ce6
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.round_message = (flags & 1) != 0
        params.duration = self.read_int32
        params.w = self.read_int32
        params.h = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_documentAttributeFilename(self):
        constructor = 0x15590068
        params = Map()
        params.file_name = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_documentAttributeImageSize(self):
        constructor = 0x6c37c15c
        params = Map()
        params.w = self.read_int32
        params.h = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_inputStickerSetID(self):
        constructor = 0x9de7a269
        params = Map()
        params.id = self.read_int64
        params.access_hash = self.read_int64
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_inputStickerSetShortName(self):
        constructor = 0x861cc8a0
        params = Map()
        params.short_name = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_inputStickerSetEmpty(self):
        constructor = 0xffb62b95
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def input_sticker_set_deserialize(self, constructor):
        result = None
        if constructor == 0xffb62b95:
            result = self._tl_inputStickerSetEmpty()
        elif constructor == 0x9de7a269:
            result = self._tl_inputStickerSetID()
        elif constructor == 0x861cc8a0:
            result = self._tl_inputStickerSetShortName()
        assert (result is not None), "constructor hex={0}, int={1} not defined".format(hex(constructor), constructor)
        return result

    def _tl_maskCoords(self):
        constructor = 0xaed6dbb2
        params = Map()
        params.n = self.read_int32
        params.x = self.read_double
        params.y = self.read_double
        params.zoom = self.read_double
        self.instances.append(inspect.stack()[0][3])
        return params

    def mask_coords_deserialize(self, constructor):
        assert (constructor == 0xaed6dbb2), "{} asseratation".format(inspect.stack()[0][3])
        result = self._tl_maskCoords()
        self.instances.append(inspect.stack()[0][3])
        return result

    def _tl_documentAttributeSticker(self):
        constructor = 0x6319d612
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.mask = (flags & 2) != 0
        params.alt = self.read_string
        params.stickerset = self.input_sticker_set_deserialize(self.read_int32)
        if (flags & 1) != 0:
            params.mask_coords = self.mask_coords_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_documentAttributeVideo_layer65(self):
        constructor = 0x5910cccb
        params = Map()
        params.duration = self.read_int32
        params.w = self.read_int32
        params.h = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_documentAttributeAnimated(self):
        constructor = 0x11b58939
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_documentAttributeSticker_layer55(self):
        constructor = 0x3a556302
        params = Map()
        params.alt = self.read_string
        params.stickerset = self.input_sticker_set_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_documentAttributeAudio_old(self):
        constructor = 0x51448e5
        params = Map()
        params.duration = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_documentAttributeAudio_layer45(self):
        constructor = 0xded218e0
        params = Map()
        params.duration = self.read_int32
        params.title = self.read_string
        params.performer = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_documentAttributeSticker_old(self):
        constructor = 0xfb0a5727
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_documentAttributeHasStickers(self):
        constructor = 0x9801d2f7
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_documentAttributeSticker_old2(self):
        constructor = 0x994c9882
        params = Map()
        params.alt = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def document_attribute_deserialize(self, constructor):
        result = None
        if constructor == 0x3a556302:
            result = self._tl_documentAttributeSticker_layer55()
        elif constructor == 0x51448e5:
            result = self._tl_documentAttributeAudio_old()
        elif constructor == 0x6319d612:
            result = self._tl_documentAttributeSticker()
        elif constructor == 0x11b58939:
            result = self._tl_documentAttributeAnimated()
        elif constructor == 0x15590068:
            result = self._tl_documentAttributeFilename()
        elif constructor == 0xef02ce6:
            result = self._tl_documentAttributeVideo()
        elif constructor == 0x5910cccb:
            result = self._tl_documentAttributeVideo_layer65()
        elif constructor == 0xded218e0:
            result = self._tl_documentAttributeAudio_layer45()
        elif constructor == 0xfb0a5727:
            result = self._tl_documentAttributeSticker_old()
        elif constructor == 0x9801d2f7:
            result = self._tl_documentAttributeHasStickers()
        elif constructor == 0x994c9882:
            result = self._tl_documentAttributeSticker_old2()
        elif constructor == 0x6c37c15c:
            result = self._tl_documentAttributeImageSize()
        elif constructor == 0x9852f9c6:
            result = self._tl_documentAttributeAudio()
        assert (result is not None), "constructor hex={0}, int={1} not defined".format(hex(constructor), constructor)
        return result

    def _tl_document(self):
        constructor = 0x9ba29cc1
        params = Map()
        flags = self.read_int32
        params.flags = flags

        params.id = self.read_int64
        params.access_hash = self.read_int64
        params.file_reference = self.read_bytes
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.mime_type = self.read_string
        params.size = self.read_int32
        if (flags & 1) != 0:
            magic = self.read_int32
            assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
            count = self.read_int32
            thumbs = list()
            for i in range(0, count):
                obj = self.photo_size_deserialize(self.read_int32)
                if obj is None:
                    return
                thumbs.append(obj)
            params.thumbs = thumbs
        params.dc_id = self.read_int32
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        attributes = list()
        for i in range(0, count):
            obj = self.document_attribute_deserialize(self.read_int32)
            if obj is None:
                return
            attributes.append(obj)
        params.attributes = attributes
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_document_layer92(self):
        constructor = 0x59534e4c
        params = Map()
        params.id = self.read_int64
        params.access_hash = self.read_int64
        params.file_reference = self.read_bytes
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.mime_type = self.read_string
        params.size = self.read_int32
        params.thumb = self.photo_size_deserialize(self.read_int32)
        params.dc_id = self.read_int32
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        attributes = list()
        for i in range(0, count):
            obj = self.document_attribute_deserialize(self.read_int32)
            if obj is None:
                return
            attributes.append(obj)
        params.attributes = attributes
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_document_layer82(self):
        constructor = 0x87232bc7
        params = Map()
        params.id = self.read_int64
        params.access_hash = self.read_int64
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.mime_type = self.read_string
        params.size = self.read_int32
        params.thumb = self.photo_size_deserialize(self.read_int32)
        params.dc_id = self.read_int32
        params.version = self.read_int32
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        attributes = list()
        for i in range(0, count):
            obj = self.document_attribute_deserialize(self.read_int32)
            if obj is None:
                return
            attributes.append(obj)
        params.attributes = attributes
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_documentEncrypted(self):
        constructor = 0x55555556
        params = Map()
        params.id = self.read_int64
        params.access_hash = self.read_int64
        date = self.read_int32
        params.date = self.time_from_ts(date)
        try:
            params.mime_type = self.read_string
        except Exception:
            params.mime_type = "audio/ogg"
        params.size = self.read_int32
        params.thumb = self.photo_size_deserialize(self.read_int32)
        params.dc_id = self.read_int32
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        attributes = list()
        for i in range(0, count):
            obj = self.document_attribute_deserialize(self.read_int32)
            if obj is None:
                return
            attributes.append(obj)
        params.attributes = attributes
        params.key = self.read_bytes
        params.iv = self.read_bytes
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_documentEmpty(self):
        constructor = 0x36f8c871
        params = Map()
        params.id = self.read_int64
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_document_old(self):
        constructor = 0x9efc6326
        params = Map()
        params.id = self.read_int64
        params.access_hash = self.read_int64
        params.user_id = self.read_int32
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.file_name = self.read_string
        params.mime_type = self.read_string
        params.size = self.read_int32
        params.thumb = self.photo_size_deserialize(self.read_int32)
        params.dc_id = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_documentEncrypted_old(self):
        constructor = 0x55555556
        params = Map()
        params.id = self.read_int64
        params.access_hash = self.read_int64
        params.user_id = self.read_int32
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.file_name = self.read_string
        params.mime_type = self.read_string
        params.size = self.read_int32
        params.thumb = self.photo_size_deserialize(self.read_int32)
        params.dc_id = self.read_int32
        params.key = self.read_bytes
        params.iv = self.read_bytes
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_document_layer53(self):
        constructor = 0xf9a39f4f
        params = Map()
        params.id = self.read_int64
        params.access_hash = self.read_int64
        params.mime_type = self.read_string
        params.size = self.read_int32
        params.thumb = self.photo_size_deserialize(self.read_int32)
        params.dc_id = self.read_int32
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        attributes = list()
        for i in range(0, count):
            obj = self.document_attribute_deserialize(self.read_int32)
            if obj is None:
                return
            attributes.append(obj)
        params.attributes = attributes
        self.instances.append(inspect.stack()[0][3])
        return params

    def document_deserialize(self, constructor):
        result = None
        if constructor == 0x9ba29cc1:
            result = self._tl_document()
        elif constructor == 0x59534e4c:
            result = self._tl_document_layer92()
        elif constructor == 0x87232bc7:
            result = self._tl_document_layer82()
        elif constructor == 0x55555556:
            result = self._tl_documentEncrypted_old()
        elif constructor == 0x9efc6326:
            result = self._tl_document_old()
        elif constructor == 0x36f8c871:
            result = self._tl_documentEmpty()
        elif constructor == 0x55555558:
            result = self._tl_documentEncrypted()
        elif constructor == 0xf9a39f4f:
            result = self._tl_document_layer53()
        assert (result is not None), "constructor hex={0}, int={1} not defined".format(hex(constructor), constructor)
        return result

    def _tl_messageMediaDocument(self):
        constructor = 0x9cb070d7
        params = Map()
        flags = self.read_int32
        params.flags = flags
        if (flags & 1) != 0:
            params.document = self.document_deserialize(self.read_int32)
        else:
            params.document = self._tl_documentEmpty()
        if (flags & 2) != 0:
            params.caption = self.read_string
        if (flags & 4) != 0:
            params.ttl_seconds = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageMediaDocument_layer72(self):
        constructor = 0x7c4414d3
        params = Map()
        flags = self.read_int32
        params.flags = flags
        if (flags & 1) != 0:
            params.document = self.document_deserialize(self.read_int32)
        else:
            params.document = self._tl_documentEmpty()
        if (flags & 2) != 0:
            params.caption = self.read_string
        if (flags & 4) != 0:
            params.ttl_seconds = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageMediaDocument_layer68(self):
        constructor = 0xf3e02ea8
        params = Map()
        params.document = self.document_deserialize(self.read_int32)
        params.caption = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_photoEmpty(self):
        constructor = 0x2331b22d
        params = Map()
        params.id = self.read_int64
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageMediaPhoto(self):
        constructor = 0x695150d7
        params = Map()
        flags = self.read_int32
        params.flags = flags
        if (flags & 1) != 0:
            params.photo = self.photo_deserialize(self.read_int32)
        else:
            params.photo = self._tl_photoEmpty()
        if (flags & 2) != 0:
            params.caption = self.read_string
        if (flags & 4) != 0:
            params.ttl_seconds = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageMediaPhoto_layer72(self):
        constructor = 0xb5223b0f
        params = Map()
        flags = self.read_int32
        params.flags = flags
        if (flags & 1) != 0:
            params.photo = self.photo_deserialize(self.read_int32)
        else:
            params.photo = self._tl_photoEmpty()
        if (flags & 2) != 0:
            params.caption = self.read_string
        if (flags & 4) != 0:
            params.ttl_seconds = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageMediaContact(self):
        constructor = 0x5e7d2f39
        params = Map()
        params.phone_number = self.read_string
        params.first_name = self.read_string
        params.last_name = self.read_string
        params.user_id = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageMediaPhoto_layer68(self):
        constructor = 0x3d8ce53d
        params = Map()
        params.photo = self.photo_deserialize(self.read_int32)
        params.caption = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageMediaUnsupported_old(self):
        constructor = 0x29632a36
        params = Map()
        params.bytes = self.read_bytes
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_audioEmpty_layer45(self):
        constructor = 0x586988d8
        params = Map()
        params.id = self.read_int64
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_audio_layer45(self):
        constructor = 0xf9e35055
        params = Map()
        params.id = self.read_int64
        params.access_hash = self.read_int64
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.duration = self.read_int32
        params.mime_type = self.read_string
        params.size = self.read_int32
        params.dc_id = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_audio_old(self):
        constructor = 0x427425e7
        params = Map()
        params.id = self.read_int64
        params.access_hash = self.read_int64
        params.user_id = self.read_int32
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.duration = self.read_int32
        params.size = self.read_int32
        params.dc_id = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_audioEncrypted(self):
        constructor = 0x555555F6
        params = Map()
        params.id = self.read_int64
        params.access_hash = self.read_int64
        params.user_id = self.read_int32
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.duration = self.read_int32
        params.size = self.read_int32
        params.dc_id = self.read_int32
        params.key = self.read_bytes
        params.iv = self.read_bytes
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_audio_old2(self):
        constructor = 0xc7ac6496
        params = Map()
        params.id = self.read_int64
        params.access_hash = self.read_int64
        params.user_id = self.read_int32
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.duration = self.read_int32
        params.mime_type = self.read_string
        params.size = self.read_int32
        params.dc_id = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def audio_deserialize(self, constructor):
        result = None
        if constructor == 0x586988d8:
            result = self._tl_audioEmpty_layer45()
        elif constructor == 0xf9e35055:
            result = self._tl_audio_layer45()
        elif constructor == 0x427425e7:
            result = self._tl_audio_old()
        elif constructor == 0x555555F6:
            result = self._tl_audioEncrypted()
        elif constructor == 0xc7ac6496:
            result = self._tl_audio_old2()
        assert (result is not None), "constructor hex={0}, int={1} not defined".format(hex(constructor), constructor)
        return result

    def _tl_messageMediaAudio_layer45(self):
        constructor = 0xc6b68300
        params = Map()
        params.audio_unused = self.audio_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageMediaPhoto_old(self):
        constructor = 0xc8c45a2a
        params = Map()
        params.photo = self.photo_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageMediaUnsupported(self):
        constructor = 0x9f84f49e
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageMediaVenue_layer71(self):
        constructor = 0x7912b71f
        params = Map()
        params.geo = self.geo_point_deserialize(self.read_int32)
        params.title = self.read_string
        params.address = self.read_string
        params.provider = self.read_string
        params.venue_id = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageMediaVenue(self):
        constructor = 0x2ec0533f
        params = Map()
        params.geo = self.geo_point_deserialize(self.read_int32)
        params.title = self.read_string
        params.address = self.read_string
        params.provider = self.read_string
        params.venue_id = self.read_string
        params.venue_type = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_video_old3(self):
        constructor = 0xee9f4a4d
        params = Map()
        params.id = self.read_int64
        params.access_hash = self.read_int64
        params.user_id = self.read_int32
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.duration = self.read_int32
        params.size = self.read_int32
        params.thumb = self.photo_size_deserialize(self.read_int32)
        params.dc_id = self.read_int32
        params.w = self.read_int32
        params.h = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_video_layer45(self):
        constructor = 0xf72887d3
        params = Map()
        params.id = self.read_int64
        params.access_hash = self.read_int64
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.duration = self.read_int32
        params.mime_type = self.read_string
        params.size = self.read_int32
        params.thumb = self.photo_size_deserialize(self.read_int32)
        params.dc_id = self.read_int32
        params.w = self.read_int32
        params.h = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_videoEncrypted(self):
        constructor = 0x55555553
        params = Map()
        params.id = self.read_int64
        params.access_hash = self.read_int64
        params.user_id = self.read_int32
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.caption = self.read_string
        params.duration = self.read_int32
        params.size = self.read_int32
        params.thumb = self.photo_size_deserialize(self.read_int32)
        params.dc_id = self.read_int32
        params.w = self.read_int32
        params.h = self.read_int32
        params.key = self.read_bytes
        params.iv = self.read_bytes
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_video_old(self):
        constructor = 0x5a04a49f
        params = Map()
        params.id = self.read_int64
        params.access_hash = self.read_int64
        params.user_id = self.read_int32
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.caption = self.read_string
        params.duration = self.read_int32
        params.size = self.read_int32
        params.thumb = self.photo_size_deserialize(self.read_int32)
        params.dc_id = self.read_int32
        params.w = self.read_int32
        params.h = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_video_old2(self):
        constructor = 0x388fa391
        params = Map()
        params.id = self.read_int64
        params.access_hash = self.read_int64
        params.user_id = self.read_int32
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.caption = self.read_string
        params.duration = self.read_int32
        params.mime_type = self.read_string
        params.size = self.read_int32
        params.thumb = self.photo_size_deserialize(self.read_int32)
        params.dc_id = self.read_int32
        params.w = self.read_int32
        params.h = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_videoEmpty_layer45(self):
        constructor = 0xc10658a8
        params = Map()
        params.id = self.read_int64
        self.instances.append(inspect.stack()[0][3])
        return params

    def video_deserialize(self, constructor):
        result = None
        if constructor == 0xee9f4a4d:
            result = self._tl_video_old3()
        elif constructor == 0xf72887d3:
            result = self._tl_video_layer45()
        elif constructor == 0x55555553:
            result = self._tl_videoEncrypted()
        elif constructor == 0x5a04a49f:
            result = self._tl_video_old()
        elif constructor == 0x388fa391:
            result = self._tl_video_old2()
        elif constructor == 0xc10658a8:
            result = self._tl_videoEmpty_layer45()
        assert (result is not None), "constructor hex={0}, int={1} not defined".format(hex(constructor), constructor)
        return result

    def _tl_messageMediaVideo_old(self):
        constructor = 0xa2d24290
        params = Map()
        params.video_unused = self.video_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageMediaDocument_old(self):
        constructor = 0x2fda2204
        params = Map()
        document = self.document_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageMediaVideo_layer45(self):
        constructor = 0x5bcf1675
        params = Map()
        params.video_unused = self.video_deserialize(self.read_int32)
        params.caption = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_webDocument(self):
        constructor = 0xc61acbd8
        params = Map()
        params.url = self.read_string
        params.access_hash = self.read_int64
        params.size = self.read_int32
        params.mime_type = self.read_string
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        attributes = list()
        for i in range(0, count):
            obj = self.document_attribute_deserialize(self.read_int32)
            if obj is None:
                return
            attributes.append(obj)
        params.attributes = attributes
        params.dc_id = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def web_document_deserialize(self, constructor):
        assert (constructor == 0xc61acbd8), "{} asseratation".format(inspect.stack()[0][3])
        result = self._tl_webDocument()
        self.instances.append(inspect.stack()[0][3])
        return result

    def _tl_messageMediaInvoice(self):
        constructor = 0x84551347
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.shipping_address_requested = (flags & 2) != 0
        params.test = (flags & 8) != 0
        params.title = self.read_string
        params.description = self.read_string
        if (flags & 1) != 0:
            params.photo = self.web_document_deserialize(self.read_int32)
        if (flags & 4) != 0:
            params.receipt_msg_id = self.read_int32
        params.currency = self.read_string
        params.total_amount = self.read_int64
        params.start_param = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageMediaGeo(self):
        constructor = 0x56e0d474
        params = Map()
        params.geo = self.geo_point_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageMediaGeoLive(self):
        constructor = 0x7c3c2609
        params = Map()
        params.geo = self.geo_point_deserialize(self.read_int32)
        params.period = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_game(self):
        constructor = 0xbdf9653b
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.id = self.read_int64
        params.access_hash = self.read_int64
        params.short_name = self.read_string
        params.title = self.read_string
        params.description = self.read_string
        params.photo = self.photo_deserialize(self.read_int32)
        if (flags & 1) != 0:
            params.document = self.document_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def game_deserialize(self, constructor):
        assert (constructor == 0xbdf9653b), "{} asseratation".format(inspect.stack()[0][3])
        result = self._tl_game()
        self.instances.append(inspect.stack()[0][3])
        return result

    def _tl_poll_answer_votes(self):
        constructor = 0x3b6ddad2
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.chosen = (flags & 1) != 0
        params.option = self.read_bytes
        params.voters = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def poll_answer_votes_deserialize(self, constructor):
        assert (constructor == 0x3b6ddad2), "{} asseratation".format(inspect.stack()[0][3])
        result = self._tl_poll_answer_votes()
        self.instances.append(inspect.stack()[0][3])
        return result

    def _tl_messageMediaGame(self):
        constructor = 0xfdb19008
        params = Map()
        params.game = self.game_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_poll_result(self):
        constructor = 0x5755785a
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.min = (flags & 1) != 0
        if (flags & 2) != 0:
            magic = self.read_int32
            assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
            count = self.read_int32
            results = list()
            for i in range(0, count):
                obj = self.poll_answer_votes_deserialize(self.read_int32)
                if obj is None:
                    return
                results.append(obj)
            params.results = results
        if (flags & 4) != 0:
            params.total_votes = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def poll_result_deserialize(self, constructor):
        assert (constructor == 0x5755785a), "{} asseratation".format(inspect.stack()[0][3])
        result = self._tl_poll_result()
        self.instances.append(inspect.stack()[0][3])
        return result

    def _tl_poll_answer(self):
        constructor = 0x6ca9c2e9
        params = Map()
        params.text = self.read_string
        params.option = self.read_bytes
        self.instances.append(inspect.stack()[0][3])
        return params

    def poll_answer_deserialize(self, constructor):
        assert (constructor == 0x6ca9c2e9), "{} asseratation".format(inspect.stack()[0][3])
        result = self._tl_poll_answer()
        self.instances.append(inspect.stack()[0][3])
        return result

    def _tl_poll(self):
        constructor = 0xd5529d06
        params = Map()
        flags = self.read_int32
        params.id = self.read_int64
        params.flags = flags
        params.closed = (flags & 1) != 0
        params.question = self.read_string
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        answers = list()
        for i in range(0, count):
            obj = self.poll_answer_deserialize(self.read_int32)
            if obj is None:
                return
            answers.append(obj)
        params.answers = answers

        self.instances.append(inspect.stack()[0][3])
        return params

    def poll_deserialize(self, constructor):
        assert (constructor == 0xd5529d06), "{} asseratation".format(inspect.stack()[0][3])
        result = self._tl_poll()
        self.instances.append(inspect.stack()[0][3])
        return result

    def _tl_messageMediaPoll(self):
        constructor = 0x4bd6e798
        params = Map()
        params.poll = self.poll_deserialize(self.read_int32)
        params.results = self.poll_result_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def message_media_deserialize(self, constructor):
        result = None
        if constructor == 0x29632a36:
            result = self._tl_messageMediaUnsupported_old()
        elif constructor == 0xc6b68300:
            result = self._tl_messageMediaAudio_layer45()
        elif constructor == 0xc8c45a2a:
            result = self._tl_messageMediaPhoto_old()
        elif constructor == 0x9f84f49e:
            result = self._tl_messageMediaUnsupported()
        elif constructor == 0x3ded6320:
            result = self._tl_messageMediaEmpty()
        elif constructor == 0x7912b71f:
            result = self._tl_messageMediaVenue_layer71()
        elif constructor == 0x7c3c2609:
            result = self._tl_messageMediaGeoLive()
        elif constructor == 0x2ec0533f:
            result = self._tl_messageMediaVenue()
        elif constructor == 0xa2d24290:
            result = self._tl_messageMediaVideo_old()
        elif constructor == 0x2fda2204:
            result = self._tl_messageMediaDocument_old()
        elif constructor == 0xf3e02ea8:
            result = self._tl_messageMediaDocument_layer68()
        elif constructor == 0xfdb19008:
            result = self._tl_messageMediaGame()
        elif constructor == 0x7c4414d3:
            result = self._tl_messageMediaDocument_layer72()
        elif constructor == 0x5e7d2f39:
            result = self._tl_messageMediaContact()
        elif constructor == 0x3d8ce53d:
            result = self._tl_messageMediaPhoto_layer68()
        elif constructor == 0x5bcf1675:
            result = self._tl_messageMediaVideo_layer45()
        elif constructor == 0x56e0d474:
            result = self._tl_messageMediaGeo()
        elif constructor == 0xa32dd600:
            result = self._tl_messageMediaWebPage()
        elif constructor == 0x84551347:
            result = self._tl_messageMediaInvoice()
        elif constructor == 0xb5223b0f:
            result = self._tl_messageMediaPhoto_layer72()
        elif constructor == 0x695150d7:
            result = self._tl_messageMediaPhoto()
        elif constructor == 0x4bd6e798:
            result = self._tl_messageMediaPoll()
        elif constructor == 0x9cb070d7:
            result = self._tl_messageMediaDocument()
        if result is not None and result.video_unused is not None:
            mediaDocument = self._tl_messageMediaDocument()
            if '_tl_videoEncrypted' in self.instances:
                mediaDocument.document = self._tl_documentEncrypted()
                mediaDocument.document.key = result.video_unused.key
                mediaDocument.document.iv = result.video_unused.iv
            else:
                mediaDocument.document = self._tl_document()
            mediaDocument.flags = 3
            mediaDocument.document.id = result.video_unused.id
            mediaDocument.document.access_hash = result.video_unused.access_hash
            mediaDocument.document.date = result.video_unused.date
            if result.video_unused.mime_type is not None:
                mediaDocument.document.mime_type = result.video_unused.mime_type
            else:
                mediaDocument.document.mime_type = "video/mp4"
            mediaDocument.document.size = result.video_unused.size
            mediaDocument.document.thumb = result.video_unused.thumb
            mediaDocument.document.dc_id = result.video_unused.dc_id
            mediaDocument.caption = result.caption
            attributeVideo = self._tl_documentAttributeVideo()
            attributeVideo.w = result.video_unused.w
            attributeVideo.h = result.video_unused.h
            attributeVideo.duration = result.video_unused.duration
            mediaDocument.document.attributes = list()
            mediaDocument.document.attributes.append(attributeVideo)
            result = mediaDocument
            if mediaDocument.caption is None:
                mediaDocument.caption = ""
        elif result is not None and result.audio_unused is not None:
            mediaDocument = self._tl_messageMediaDocument()
            if '_tl_audioEncrypted' in self.instances:
                mediaDocument.document = self._tl_documentEncrypted()
                mediaDocument.document.key = result.audio_unused.key
                mediaDocument.document.iv = result.audio_unused.iv
            else:
                mediaDocument.document = self._tl_document()
            mediaDocument.flags = 3
            mediaDocument.document.id = result.audio_unused.id
            mediaDocument.document.access_hash = result.audio_unused.access_hash
            mediaDocument.document.date = result.audio_unused.date
            if result.audio_unused.mime_type is not None:
                mediaDocument.document.mime_type = result.audio_unused.mime_type
            else:
                mediaDocument.document.mime_type = "audio/ogg"
            mediaDocument.document.size = result.audio_unused.size
            mediaDocument.document.thumb = self._tl_photoSizeEmpty()
            mediaDocument.document.thumb.type = "s"
            mediaDocument.document.dc_id = result.audio_unused.dc_id
            mediaDocument.caption = result.caption
            attributeAudio = self._tl_documentAttributeAudio()
            attributeAudio.duration = result.audio_unused.duration
            attributeAudio.voice = True
            mediaDocument.document.attributes = list()
            mediaDocument.document.attributes.append(attributeAudio)
            result = mediaDocument
            if mediaDocument.caption is None:
                mediaDocument.caption = ""
        assert (result is not None), "constructor hex={0}, int={1} not defined".format(hex(constructor), constructor)
        return result

    def _tl_messageMediaEmpty(self):
        constructor = 0x3ded6320
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageEntityMention(self):
        constructor = 0xfa04579d
        params = Map()
        params.offset = self.read_int32
        params.length = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageEntityUrl(self):
        constructor = 0x6ed02538
        params = Map()
        params.offset = self.read_int32
        params.length = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageEntityHashtag(self):
        constructor = 0x6f635b0d
        params = Map()
        params.offset = self.read_int32
        params.length = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageEntityBold(self):
        constructor = 0xbd610bc9
        params = Map()
        params.offset = self.read_int32
        params.length = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageEntityTextUrl(self):
        constructor = 0x76a6d327
        params = Map()
        params.offset = self.read_int32
        params.length = self.read_int32
        params.url = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageEntityItalic(self):
        constructor = 0x826f8b60
        params = Map()
        params.offset = self.read_int32
        params.length = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageEntityBotCommand(self):
        constructor = 0x6cef8ac7
        params = Map()
        params.offset = self.read_int32
        params.length = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageEntityEmail(self):
        constructor = 0x64e475c2
        params = Map()
        params.offset = self.read_int32
        params.length = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageEntityPre(self):
        constructor = 0x73924be0
        params = Map()
        params.offset = self.read_int32
        params.length = self.read_int32
        params.language = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageEntityUnknown(self):
        constructor = 0xbb92ba95
        params = Map()
        params.offset = self.read_int32
        params.length = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageEntityMentionName(self):
        constructor = 0x352dca58
        params = Map()
        params.offset = self.read_int32
        params.length = self.read_int32
        params.user_id = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_inputUserEmpty(self):
        constructor = 0xb98886cf
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_inputUserSelf(self):
        constructor = 0xf7c1b13f
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_inputUser(self):
        constructor = 0xd8292816
        params = Map()
        params.user_id = self.read_int32
        params.access_hash = self.read_int64
        self.instances.append(inspect.stack()[0][3])
        return params

    def input_user_deserialize(self, constructor):
        result = None
        if constructor == 0xb98886cf:
            result = self._tl_inputUserEmpty()
        elif constructor == 0xf7c1b13f:
            result = self._tl_inputUserSelf()
        elif constructor == 0xd8292816:
            result = self._tl_inputUser()
        assert (result is not None), "constructor hex={0}, int={1} not defined".format(hex(constructor), constructor)
        return result

    def _tl_inputMessageEntityMentionName(self):
        constructor = 0x208e68c9
        params = Map()
        params.offset = self.read_int32
        params.length = self.read_int32
        params.user_id = self.input_user_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageEntityCode(self):
        constructor = 0x28a20571
        params = Map()
        params.offset = self.read_int32
        params.length = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageEntityPhone(self):
        constructor = 0x9b69e34b
        params = Map()
        params.offset = self.read_int32
        params.length = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def message_entity_deserialize(self, constructor):
        result = None
        if constructor == 0x76a6d327:
            result = self._tl_messageEntityTextUrl()
        elif constructor == 0x9b69e34b:
            result = self._tl_messageEntityPhone()
        elif constructor == 0x6cef8ac7:
            result = self._tl_messageEntityBotCommand()
        elif constructor == 0x64e475c2:
            result = self._tl_messageEntityEmail()
        elif constructor == 0x73924be0:
            result = self._tl_messageEntityPre()
        elif constructor == 0xbb92ba95:
            result = self._tl_messageEntityUnknown()
        elif constructor == 0x6ed02538:
            result = self._tl_messageEntityUrl()
        elif constructor == 0x826f8b60:
            result = self._tl_messageEntityItalic()
        elif constructor == 0xfa04579d:
            result = self._tl_messageEntityMention()
        elif constructor == 0x352dca58:
            result = self._tl_messageEntityMentionName()
        elif constructor == 0x208e68c9:
            result = self._tl_inputMessageEntityMentionName()
        elif constructor == 0xbd610bc9:
            result = self._tl_messageEntityBold()
        elif constructor == 0x6f635b0d:
            result = self._tl_messageEntityHashtag()
        elif constructor == 0x28a20571:
            result = self._tl_messageEntityCode()
        assert (result is not None), "constructor hex={0}, int={1} not defined".format(hex(constructor), constructor)
        return result

    def _tl_keyboardButtonCallback(self):
        constructor = 0x683a5e46
        params = Map()
        params.text = self.read_string
        params.data = self.read_bytes
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_keyboardButtonRequestPhone(self):
        constructor = 0xb16a6c29
        params = Map()
        params.text = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_keyboardButtonGame(self):
        constructor = 0x50f41ccf
        params = Map()
        params.text = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_keyboardButtonUrl(self):
        constructor = 0x258aff05
        params = Map()
        params.text = self.read_string
        params.url = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_keyboardButtonSwitchInline(self):
        constructor = 0x568a748
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.same_peer = (flags & 1) != 0
        params.text = self.read_string
        params.query = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_keyboardButtonRequestGeoLocation(self):
        constructor = 0xfc796b3f
        params = Map()
        params.text = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_keyboardButtonBuy(self):
        constructor = 0xafd93fbb
        params = Map()
        params.text = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_keyboardButton(self):
        constructor = 0xa2fa4880
        params = Map()
        params.text = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def keyboard_button_deserialize(self, constructor):
        result = None
        if constructor == 0xb16a6c29:
            result = self._tl_keyboardButtonRequestPhone()
        elif constructor == 0x50f41ccf:
            result = self._tl_keyboardButtonGame()
        elif constructor == 0x258aff05:
            result = self._tl_keyboardButtonUrl()
        elif constructor == 0x568a748:
            result = self._tl_keyboardButtonSwitchInline()
        elif constructor == 0xfc796b3f:
            result = self._tl_keyboardButtonRequestGeoLocation()
        elif constructor == 0xafd93fbb:
            result = self._tl_keyboardButtonBuy()
        elif constructor == 0x683a5e46:
            result = self._tl_keyboardButtonCallback()
        elif constructor == 0xa2fa4880:
            result = self._tl_keyboardButton()
        assert (result is not None), "constructor hex={0}, int={1} not defined".format(hex(constructor), constructor)
        return result

    def _tl_keyboardButtonRow(self):
        constructor = 0x77608b83
        params = Map()
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        buttons = list()
        for i in range(0, count):
            obj = self.keyboard_button_deserialize(self.read_int32)
            if obj is None:
                return
            buttons.append(obj)
        params.buttons = buttons
        self.instances.append(inspect.stack()[0][3])
        return params

    def keyboard_button_row_deserialize(self, constructor):
        assert (constructor == 0x77608b83), "{} asseratation".format(inspect.stack()[0][3])
        result = self._tl_keyboardButtonRow()
        self.instances.append(inspect.stack()[0][3])
        return result

    def _tl_replyInlineMarkup(self):
        constructor = 0x48a30254
        params = Map()
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        rows = list()
        for i in range(0, count):
            obj = self.keyboard_button_row_deserialize(self.read_int32)
            if obj is None:
                return
            rows.append(obj)
        params.rows = rows
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_replyKeyboardHide(self):
        constructor = 0xa03e5b85
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.selective = (flags & 4) != 0
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_replyKeyboardForceReply(self):
        constructor = 0xf4108aa0
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.single_use = (flags & 2) != 0
        params.selective = (flags & 4) != 0
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_replyKeyboardMarkup(self):
        constructor = 0x3502758c
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.resize = (flags & 1) != 0
        params.single_use = (flags & 2) != 0
        params.selective = (flags & 4) != 0
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        rows = list()
        for i in range(0, count):
            obj = self.keyboard_button_row_deserialize(self.read_int32)
            if obj is None:
                return
            rows.append(obj)
        params.rows = rows
        self.instances.append(inspect.stack()[0][3])
        return params

    def reply_markup_deserialize(self, constructor):
        result = None
        if constructor == 0x48a30254:
            result = self._tl_replyInlineMarkup()
        elif constructor == 0xa03e5b85:
            result = self._tl_replyKeyboardHide()
        elif constructor == 0xf4108aa0:
            result = self._tl_replyKeyboardForceReply()
        elif constructor == 0x3502758c:
            result = self._tl_replyKeyboardMarkup()
        assert (result is not None), "constructor hex={0}, int={1} not defined".format(hex(constructor), constructor)
        return result

    def _tl_messageActionChatAddUser(self):
        constructor = 0x488a7337
        params = Map()
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        users = list()
        for i in range(0, count):
            users.append(self.read_int32)
        params.users = users
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageActionUserJoined(self):
        constructor = 0x55555550
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_decryptedMessageActionNoop(self):
        constructor = 0xa82fdd63
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_decryptedMessageActionAcceptKey(self):
        constructor = 0x6fe1735b
        params = Map()
        params.exchange_id = self.read_int64
        params.g_b = self.read_bytes
        params.key_fingerprint = self.read_int64
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_decryptedMessageActionNotifyLayer(self):
        constructor = 0xf3048883
        params = Map()
        params.layer = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_decryptedMessageActionSetMessageTTL(self):
        constructor = 0xa1733aec
        params = Map()
        params.ttl_seconds = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_decryptedMessageActionDeleteMessages(self):
        constructor = 0x65614304
        params = Map()
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        random_ids = list()
        for i in range(0, count):
            random_ids.append(self.read_int64)
        params.random_ids = random_ids
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_decryptedMessageActionCommitKey(self):
        constructor = 0xec2e0b9b
        params = Map()
        params.exchange_id = self.read_int64
        params.key_fingerprint = self.read_int64
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_decryptedMessageActionAbortKey(self):
        constructor = 0xdd05ec6b
        params = Map()
        params.exchange_id = self.read_int64
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_decryptedMessageActionFlushHistory(self):
        constructor = 0x6719e45c
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_sendMessageGamePlayAction(self):
        constructor = 0xdd6a8f48
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_sendMessageRecordAudioAction(self):
        constructor = 0xd52f73f7
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_sendMessageUploadVideoAction_old(self):
        constructor = 0x92042ff7
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_sendMessageUploadAudioAction_old(self):
        constructor = 0xe6ac8a6f
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_sendMessageUploadAudioAction(self):
        constructor = 0xf351d7ab
        params = Map()
        params.progress = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_sendMessageUploadPhotoAction(self):
        constructor = 0xd1d34a26
        params = Map()
        params.progress = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_sendMessageUploadDocumentAction_old(self):
        constructor = 0x8faee98e
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_sendMessageUploadVideoAction(self):
        constructor = 0xe9763aec
        params = Map()
        params.progress = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_sendMessageCancelAction(self):
        constructor = 0xfd5ec8f5
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_sendMessageGeoLocationAction(self):
        constructor = 0x176f8ba1
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_sendMessageChooseContactAction(self):
        constructor = 0x628cbc6f
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_sendMessageRecordRoundAction(self):
        constructor = 0x88f27fbc
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_sendMessageUploadRoundAction(self):
        constructor = 0x243e1c66
        params = Map()
        params.progress = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_sendMessageTypingAction(self):
        constructor = 0x16bf744e
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_sendMessageUploadPhotoAction_old(self):
        constructor = 0x990a3c1a
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_sendMessageUploadDocumentAction(self):
        constructor = 0xaa0cd9e4
        params = Map()
        params.progress = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_sendMessageRecordVideoAction(self):
        constructor = 0xa187d66f
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def send_message_action_deserialize(self, constructor):
        result = None
        if constructor == 0xdd6a8f48:
            result = self._tl_sendMessageGamePlayAction()
        elif constructor == 0xd52f73f7:
            result = self._tl_sendMessageRecordAudioAction()
        elif constructor == 0x92042ff7:
            result = self._tl_sendMessageUploadVideoAction_old()
        elif constructor == 0xe6ac8a6f:
            result = self._tl_sendMessageUploadAudioAction_old()
        elif constructor == 0xf351d7ab:
            result = self._tl_sendMessageUploadAudioAction()
        elif constructor == 0xd1d34a26:
            result = self._tl_sendMessageUploadPhotoAction()
        elif constructor == 0x8faee98e:
            result = self._tl_sendMessageUploadDocumentAction_old()
        elif constructor == 0xe9763aec:
            result = self._tl_sendMessageUploadVideoAction()
        elif constructor == 0xfd5ec8f5:
            result = self._tl_sendMessageCancelAction()
        elif constructor == 0x176f8ba1:
            result = self._tl_sendMessageGeoLocationAction()
        elif constructor == 0x628cbc6f:
            result = self._tl_sendMessageChooseContactAction()
        elif constructor == 0x88f27fbc:
            result = self._tl_sendMessageRecordRoundAction()
        elif constructor == 0x243e1c66:
            result = self._tl_sendMessageUploadRoundAction()
        elif constructor == 0x16bf744e:
            result = self._tl_sendMessageTypingAction()
        elif constructor == 0x990a3c1a:
            result = self._tl_sendMessageUploadPhotoAction_old()
        elif constructor == 0xaa0cd9e4:
            result = self._tl_sendMessageUploadDocumentAction()
        elif constructor == 0xa187d66f:
            result = self._tl_sendMessageRecordVideoAction()
        assert (result is not None), "constructor hex={0}, int={1} not defined".format(hex(constructor), constructor)
        return result

    def _tl_decryptedMessageActionTyping(self):
        constructor = 0xccb27641
        params = Map()
        params.action = self.send_message_action_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_decryptedMessageActionReadMessages(self):
        constructor = 0xc4f40be
        params = Map()
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        random_ids = list()
        for i in range(0, count):
            random_ids.append(self.read_int64)
        params.random_ids = random_ids
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_decryptedMessageActionResend(self):
        constructor = 0x511110b0
        params = Map()
        params.start_seq_no = self.read_int32
        params.end_seq_no = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_decryptedMessageActionRequestKey(self):
        constructor = 0xf3c9611b
        params = Map()
        params.exchange_id = self.read_int64
        params.g_a = self.read_bytes
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_decryptedMessageActionScreenshotMessages(self):
        constructor = 0x8ac1f475
        params = Map()
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        random_ids = list()
        for i in range(0, count):
            random_ids.append(self.read_int64)
        params.random_ids = random_ids
        self.instances.append(inspect.stack()[0][3])
        return params

    def decrypted_message_action_deserialize(self, constructor):
        result = None
        if constructor == 0xa1733aec:
            result = self._tl_decryptedMessageActionSetMessageTTL()
        elif constructor == 0xf3048883:
            result = self._tl_decryptedMessageActionNotifyLayer()
        elif constructor == 0x65614304:
            result = self._tl_decryptedMessageActionDeleteMessages()
        elif constructor == 0xec2e0b9b:
            result = self._tl_decryptedMessageActionCommitKey()
        elif constructor == 0xdd05ec6b:
            result = self._tl_decryptedMessageActionAbortKey()
        elif constructor == 0x6719e45c:
            result = self._tl_decryptedMessageActionFlushHistory()
        elif constructor == 0xccb27641:
            result = self._tl_decryptedMessageActionTyping()
        elif constructor == 0x6fe1735b:
            result = self._tl_decryptedMessageActionAcceptKey()
        elif constructor == 0xc4f40be:
            result = self._tl_decryptedMessageActionReadMessages()
        elif constructor == 0x511110b0:
            result = self._tl_decryptedMessageActionResend()
        elif constructor == 0xf3c9611b:
            result = self._tl_decryptedMessageActionRequestKey()
        elif constructor == 0x8ac1f475:
            result = self._tl_decryptedMessageActionScreenshotMessages()
        elif constructor == 0xa82fdd63:
            result = self._tl_decryptedMessageActionNoop()
        assert (result is not None), "constructor hex={0}, int={1} not defined".format(hex(constructor), constructor)
        return result

    def _tl_messageEncryptedAction(self):
        constructor = 0x555555F7
        params = Map()
        params.encryptedAction = self.decrypted_message_action_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageActionHistoryClear(self):
        constructor = 0x9fbab604
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageActionChatCreate(self):
        constructor = 0xa6638b9a
        params = Map()
        params.title = self.read_string
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        users = list()
        for i in range(0, count):
            users.append(self.read_int32)
        params.users = users
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageActionChatEditPhoto(self):
        constructor = 0x7fcb13a8
        params = Map()
        params.photo = self.photo_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageActionChatDeleteUser(self):
        constructor = 0xb2ae9b0c
        params = Map()
        params.user_id = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageActionChannelCreate(self):
        constructor = 0x95d2ac92
        params = Map()
        params.title = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageActionChatDeletePhoto(self):
        constructor = 0x95e3fbef
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageActionChatEditTitle(self):
        constructor = 0xb5a1ce5a
        params = Map()
        params.title = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageActionEmpty(self):
        constructor = 0xb6aef7b0
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageActionLoginUnknownLocation(self):
        constructor = 0x555555F5
        params = Map()
        params.title = self.read_string
        params.address = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageActionChatMigrateTo(self):
        constructor = 0x51bdb021
        params = Map()
        params.channel_id = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageActionScreenshotTaken(self):
        constructor = 0x4792929b
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageActionChannelMigrateFrom(self):
        constructor = 0xb055eaee
        params = Map()
        params.title = self.read_string
        params.chat_id = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageActionCreatedBroadcastList(self):
        constructor = 0x55555557
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageActionUserUpdatedPhoto(self):
        constructor = 0x55555551
        params = Map()
        params.newUserPhoto = self.user_profile_photo_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageActionChatAddUser_old(self):
        constructor = 0x5e3cfc4b
        params = Map()
        params.user_id = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageActionTTLChange(self):
        constructor = 0x55555552
        params = Map()
        params.ttl = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageActionGeoChatCheckin(self):
        constructor = 0xc7d53de
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageActionChatJoinedByLink(self):
        constructor = 0xf89cf5e8
        params = Map()
        params.inviter_id = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageActionPinMessage(self):
        constructor = 0x94bd38ed
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageActionPhoneCall(self):
        constructor = 0x80e11a7f
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.call_id = self.read_int64
        if (flags & 1) != 0:
            params.reason = self.phone_call_discard_reason_deserialize(self.read_int32)
        if (flags & 2) != 0:
            params.duration = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageActionPaymentSent(self):
        constructor = 0x40699cd0
        params = Map()
        params.currency = self.read_string
        params.total_amount = self.read_int64
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageActionGameScore(self):
        constructor = 0x92a72876
        params = Map()
        params.game_id = self.read_int64
        params.score = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageActionGeoChatCreate(self):
        constructor = 0x6f038ebc
        params = Map()
        params.title = self.read_string
        params.address = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageActionCustomAction(self):
        constructor = 0xfae69f56
        params = Map()
        params.message = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def message_action_deserialize(self, constructor):
        result = None
        if constructor == 0x555555F5:
            result = self._tl_messageActionLoginUnknownLocation()
        elif constructor == 0x555555F7:
            result = self._tl_messageEncryptedAction()
        elif constructor == 0xfae69f56:
            result = self._tl_messageActionCustomAction()
        elif constructor == 0xa6638b9a:
            result = self._tl_messageActionChatCreate()
        elif constructor == 0x51bdb021:
            result = self._tl_messageActionChatMigrateTo()
        elif constructor == 0x4792929b:
            result = self._tl_messageActionScreenshotTaken()
        elif constructor == 0x9fbab604:
            result = self._tl_messageActionHistoryClear()
        elif constructor == 0x7fcb13a8:
            result = self._tl_messageActionChatEditPhoto()
        elif constructor == 0xb055eaee:
            result = self._tl_messageActionChannelMigrateFrom()
        elif constructor == 0x488a7337:
            result = self._tl_messageActionChatAddUser()
        elif constructor == 0xb2ae9b0c:
            result = self._tl_messageActionChatDeleteUser()
        elif constructor == 0x55555557:
            result = self._tl_messageActionCreatedBroadcastList()
        elif constructor == 0x55555550:
            result = self._tl_messageActionUserJoined()
        elif constructor == 0x55555551:
            result = self._tl_messageActionUserUpdatedPhoto()
        elif constructor == 0x5e3cfc4b:
            result = self._tl_messageActionChatAddUser_old()
        elif constructor == 0x55555552:
            result = self._tl_messageActionTTLChange()
        elif constructor == 0xc7d53de:
            result = self._tl_messageActionGeoChatCheckin()
        elif constructor == 0xf89cf5e8:
            result = self._tl_messageActionChatJoinedByLink()
        elif constructor == 0x95d2ac92:
            result = self._tl_messageActionChannelCreate()
        elif constructor == 0x94bd38ed:
            result = self._tl_messageActionPinMessage()
        elif constructor == 0x95e3fbef:
            result = self._tl_messageActionChatDeletePhoto()
        elif constructor == 0x80e11a7f:
            result = self._tl_messageActionPhoneCall()
        elif constructor == 0xb5a1ce5a:
            result = self._tl_messageActionChatEditTitle()
        elif constructor == 0x40699cd0:
            result = self._tl_messageActionPaymentSent()
        elif constructor == 0xb6aef7b0:
            result = self._tl_messageActionEmpty()
        elif constructor == 0x92a72876:
            result = self._tl_messageActionGameScore()
        elif constructor == 0x6f038ebc:
            result = self._tl_messageActionGeoChatCreate()
        assert (result is not None), "constructor hex={0}, int={1} not defined".format(hex(constructor), constructor)
        return result

    def _tl_phoneCallDiscardReasonHangup(self):
        constructor = 0x57adc690
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_phoneCallDiscardReasonBusy(self):
        constructor = 0xfaf7e8c9
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_phoneCallDiscardReasonMissed(self):
        constructor = 0x85e42301
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_phoneCallDiscardReasonDisconnect(self):
        constructor = 0xe095c1a0
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def phone_call_discard_reason_deserialize(self, constructor):
        result = None
        if constructor == 0x57adc690:
            result = self._tl_phoneCallDiscardReasonHangup()
        elif constructor == 0xfaf7e8c9:
            result = self._tl_phoneCallDiscardReasonBusy()
        elif constructor == 0x85e42301:
            result = self._tl_phoneCallDiscardReasonMissed()
        elif constructor == 0xe095c1a0:
            result = self._tl_phoneCallDiscardReasonDisconnect()
        assert (result is not None), "constructor hex={0}, int={1} not defined".format(hex(constructor), constructor)
        return result

    def _tl_userProfilePhoto(self):
        constructor = 0xecd75d8c
        params = Map()
        params.photo_id = self.read_int64
        params.photo_small = self.file_location_deserialize(self.read_int32)
        params.photo_big = self.file_location_deserialize(self.read_int32)
        params.dc_id = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_userProfilePhoto_layer97(self):
        constructor = 0xd559d8c8
        params = Map()
        params.photo_id = self.read_int64
        params.photo_small = self.file_location_deserialize(self.read_int32)
        params.photo_big = self.file_location_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_userProfilePhotoEmpty(self):
        constructor = 0x4f11bae1
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_userProfilePhoto_old(self):
        constructor = 0x990d1493
        params = Map()
        params.photo_small = self.file_location_deserialize(self.read_int32)
        params.photo_big = self.file_location_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def user_profile_photo_deserialize(self, constructor):
        result = None
        if constructor == 0xecd75d8c:
            result = self._tl_userProfilePhoto()
        elif constructor == 0x4f11bae1:
            result = self._tl_userProfilePhotoEmpty()
        elif constructor == 0xd559d8c8:
            result = self._tl_userProfilePhoto_layer97()
        elif constructor == 0x990d1493:
            result = self._tl_userProfilePhoto_old()
        assert (result is not None), "constructor hex={0}, int={1} not defined".format(hex(constructor), constructor)
        return result

    def _tl_userStatusOffline(self):
        constructor = 0x8c703f
        params = Map()
        params.expires = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_userStatusRecently(self):
        constructor = 0xe26f42f1
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_userStatusOnline(self):
        constructor = 0xedb93949
        params = Map()
        params.expires = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_userStatusLastWeek(self):
        constructor = 0x7bf09fc
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_userStatusEmpty(self):
        constructor = 0x9d05049
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_userStatusLastMonth(self):
        constructor = 0x77ebc742
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def user_status_deserialize(self, constructor):
        result = None
        if constructor == 0x8c703f:
            result = self._tl_userStatusOffline()
        elif constructor == 0x7bf09fc:
            result = self._tl_userStatusLastWeek()
        elif constructor == 0x9d05049:
            result = self._tl_userStatusEmpty()
        elif constructor == 0x77ebc742:
            result = self._tl_userStatusLastMonth()
        elif constructor == 0xedb93949:
            result = self._tl_userStatusOnline()
        elif constructor == 0xe26f42f1:
            result = self._tl_userStatusRecently()
        assert (result is not None), "constructor hex={0}, int={1} not defined".format(hex(constructor), constructor)
        return result

    def _tl_user_layer65(self):
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.self = (flags & 1024) != 0
        params.contact = (flags & 2048) != 0
        params.mutual_contact = (flags & 4096) != 0
        params.deleted = (flags & 8192) != 0
        params.bot = (flags & 16384) != 0
        params.bot_chat_history = (flags & 32768) != 0
        params.bot_nochats = (flags & 65536) != 0
        params.verified = (flags & 131072) != 0
        params.restricted = (flags & 262144) != 0
        params.min = (flags & 1048576) != 0
        params.bot_inline_geo = (flags & 2097152) != 0
        params.id = self.read_int32
        if (flags & 1) != 0:
            params.access_hash = self.read_int64
        if (flags & 2) != 0:
            params.first_name = self.read_string
        if (flags & 4) != 0:
            params.last_name = self.read_string
        if (flags & 8) != 0:
            params.username = self.read_string
        if (flags & 16) != 0:
            params.phone = self.read_string
        if (flags & 32) != 0:
            params.photo = self.user_profile_photo_deserialize(self.read_int32)
        if (flags & 64) != 0:
            params.status = self.user_status_deserialize(self.read_int32)
        if (flags & 16384) != 0:
            params.bot_info_version = self.read_int32
        if (flags & 262144) != 0:
            params.restriction_reason = self.read_string
        if (flags & 524288) != 0:
            params.bot_inline_placeholder = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_encryptedChat(self):
        constructor = 0xfa56ce36
        params = Map()
        params.id = self.read_int32
        params.access_hash = self.read_int64
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.admin_id = self.read_int32
        params.participant_id = self.read_int32
        params.g_a_or_b = self.read_bytes
        params.key_fingerprint = self.read_int64
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_encryptedChatRequested_old(self):
        constructor = 0xfda9a7b7
        params = Map()
        params.id = self.read_int32
        params.access_hash = self.read_int64
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.admin_id = self.read_int32
        params.participant_id = self.read_int32
        params.g_a = self.read_bytes
        params.nonce = self.read_bytes
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_encryptedChatRequested(self):
        constructor = 0xc878527e
        params = Map()
        params.id = self.read_int32
        params.access_hash = self.read_int64
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.admin_id = self.read_int32
        params.participant_id = self.read_int32
        params.g_a = self.read_bytes
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_encryptedChat_old(self):
        constructor = 0x6601d14f
        params = Map()
        params.id = self.read_int32
        params.access_hash = self.read_int64
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.admin_id = self.read_int32
        params.participant_id = self.read_int32
        params.g_a_or_b = self.read_bytes
        params.nonce = self.read_bytes
        params.key_fingerprint = self.read_int64
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_encryptedChatEmpty(self):
        constructor = 0xab7ec0a0
        params = Map()
        params.id = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_encryptedChatWaiting(self):
        constructor = 0x3bf703dc
        params = Map()
        params.id = self.read_int32
        params.access_hash = self.read_int64
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.admin_id = self.read_int32
        params.participant_id = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_encryptedChatDiscarded(self):
        constructor = 0x13d6dd27
        params = Map()
        params.id = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def encrypted_chat_deserialize(self, constructor):
        result = None
        if constructor == 0xfda9a7b7:
            result = self._tl_encryptedChatRequested_old()
        elif constructor == 0xc878527e:
            result = self._tl_encryptedChatRequested()
        elif constructor == 0xfa56ce36:
            result = self._tl_encryptedChat()
        elif constructor == 0x6601d14f:
            result = self._tl_encryptedChat_old()
        elif constructor == 0xab7ec0a0:
            result = self._tl_encryptedChatEmpty()
        elif constructor == 0x3bf703dc:
            result = self._tl_encryptedChatWaiting()
        elif constructor == 0x13d6dd27:
            result = self._tl_encryptedChatDiscarded()
        assert (result is not None), "constructor hex={0}, int={1} not defined".format(hex(constructor), constructor)
        return result

    def _tl_userContact_old2(self):
        constructor = 0xcab35e18
        params = Map()
        params.id = self.read_int32
        params.first_name = self.read_string
        params.last_name = self.read_string
        params.username = self.read_string
        params.access_hash = self.read_int64
        params.phone = self.read_string
        params.photo = self.user_profile_photo_deserialize(self.read_int32)
        params.status = self.user_status_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_userContact_old(self):
        constructor = 0xf2fb8319
        params = Map()
        params.id = self.read_int32
        params.first_name = self.read_string
        params.last_name = self.read_string
        params.access_hash = self.read_int64
        params.phone = self.read_string
        params.photo = self.user_profile_photo_deserialize(self.read_int32)
        params.status = self.user_status_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_user(self):
        constructor = 0x2e13f4c3
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.self = (flags & 1024) != 0
        params.contact = (flags & 2048) != 0
        params.mutual_contact = (flags & 4096) != 0
        params.deleted = (flags & 8192) != 0
        params.bot = (flags & 16384) != 0
        params.bot_chat_history = (flags & 32768) != 0
        params.bot_nochats = (flags & 65536) != 0
        params.verified = (flags & 131072) != 0
        params.restricted = (flags & 262144) != 0
        params.min = (flags & 1048576) != 0
        params.bot_inline_geo = (flags & 2097152) != 0
        params.id = self.read_int32
        if (flags & 1) != 0:
            params.access_hash = self.read_int64
        if (flags & 2) != 0:
            params.first_name = self.read_string
        if (flags & 4) != 0:
            params.last_name = self.read_string
        if (flags & 8) != 0:
            params.username = self.read_string
        if (flags & 16) != 0:
            params.phone = self.read_string
        if (flags & 32) != 0:
            params.photo = self.user_profile_photo_deserialize(self.read_int32)
        if (flags & 64) != 0:
            params.status = self.user_status_deserialize(self.read_int32)
        if (flags & 16384) != 0:
            params.bot_info_version = self.read_int32
        if (flags & 262144) != 0:
            params.restriction_reason = self.read_string
        if (flags & 524288) != 0:
            params.bot_inline_placeholder = self.read_string
        if (flags & 4194304) != 0:
            params.lang_code = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_userSelf_old(self):
        constructor = 0x720535ec
        params = Map()
        params.id = self.read_int32
        params.first_name = self.read_string
        params.last_name = self.read_string
        params.phone = self.read_string
        params.photo = self.user_profile_photo_deserialize(self.read_int32)
        params.status = self.user_status_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_userSelf_old3(self):
        constructor = 0x1c60e608
        params = Map()
        params.id = self.read_int32
        params.first_name = self.read_string
        params.last_name = self.read_string
        params.username = self.read_string
        params.phone = self.read_string
        params.photo = self.user_profile_photo_deserialize(self.read_int32)
        params.status = self.user_status_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_userDeleted_old2(self):
        constructor = 0xd6016d7a
        params = Map()
        params.id = self.read_int32
        params.first_name = self.read_string
        params.last_name = self.read_string
        params.username = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_userEmpty(self):
        constructor = 0x200250ba
        params = Map()
        params.id = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_userRequest_old(self):
        constructor = 0x22e8ceb0
        params = Map()
        params.id = self.read_int32
        params.first_name = self.read_string
        params.last_name = self.read_string
        params.access_hash = self.read_int64
        params.phone = self.read_string
        params.photo = self.user_profile_photo_deserialize(self.read_int32)
        params.status = self.user_status_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_userForeign_old(self):
        constructor = 0x5214c89d
        params = Map()
        params.id = self.read_int32
        params.first_name = self.read_string
        params.last_name = self.read_string
        params.access_hash = self.read_int64
        params.photo = self.user_profile_photo_deserialize(self.read_int32)
        params.status = self.user_status_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_userForeign_old2(self):
        constructor = 0x75cf7a8
        params = Map()
        params.id = self.read_int32
        params.first_name = self.read_string
        params.last_name = self.read_string
        params.username = self.read_string
        params.access_hash = self.read_int64
        params.photo = self.user_profile_photo_deserialize(self.read_int32)
        params.status = self.user_status_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_userRequest_old2(self):
        constructor = 0xd9ccc4ef
        params = Map()
        params.id = self.read_int32
        params.first_name = self.read_string
        params.last_name = self.read_string
        params.username = self.read_string
        params.access_hash = self.read_int64
        params.phone = self.read_string
        params.photo = self.user_profile_photo_deserialize(self.read_int32)
        params.status = self.user_status_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_userDeleted_old(self):
        constructor = 0xb29ad7cc
        params = Map()
        params.id = self.read_int32
        params.first_name = self.read_string
        params.last_name = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_user_old(self):
        constructor = 0x22e49072
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.self = (flags & 1024) != 0
        params.contact = (flags & 2048) != 0
        params.mutual_contact = (flags & 4096) != 0
        params.deleted = (flags & 8192) != 0
        params.bot = (flags & 16384) != 0
        params.bot_chat_history = (flags & 32768) != 0
        params.bot_nochats = (flags & 65536) != 0
        params.verified = (flags & 131072) != 0
        params.explicit_content = (flags & 262144) != 0
        params.id = self.read_int32
        if (flags & 1) != 0:
            params.access_hash = self.read_int64
        if (flags & 2) != 0:
            params.first_name = self.read_string
        if (flags & 4) != 0:
            params.last_name = self.read_string
        if (flags & 8) != 0:
            params.username = self.read_string
        if (flags & 16) != 0:
            params.phone = self.read_string
        if (flags & 32) != 0:
            params.photo = self.user_profile_photo_deserialize(self.read_int32)
        if (flags & 64) != 0:
            params.status = self.user_status_deserialize(self.read_int32)
        if (flags & 16384) != 0:
            params.bot_info_version = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_userSelf_old2(self):
        constructor = 0x7007b451
        params = Map()
        params.id = self.read_int32
        params.first_name = self.read_string
        params.last_name = self.read_string
        params.username = self.read_string
        params.phone = self.read_string
        params.photo = self.user_profile_photo_deserialize(self.read_int32)
        params.status = self.user_status_deserialize(self.read_int32)
        params.inactive = self.read_bool
        self.instances.append(inspect.stack()[0][3])
        return params

    def user_deserialize(self, constructor):
        result = None
        if constructor == 0xcab35e18:
            result = self._tl_userContact_old2()
        elif constructor == 0xf2fb8319:
            result = self._tl_userContact_old()
        elif constructor == 0x2e13f4c3:
            result = self._tl_user()
        elif constructor == 0x720535ec:
            result = self._tl_userSelf_old()
        elif constructor == 0x1c60e608:
            result = self._tl_userSelf_old3()
        elif constructor == 0xd6016d7a:
            result = self._tl_userDeleted_old2()
        elif constructor == 0x200250ba:
            result = self._tl_userEmpty()
        elif constructor == 0x22e8ceb0:
            result = self._tl_userRequest_old()
        elif constructor == 0x5214c89d:
            result = self._tl_userForeign_old()
        elif constructor == 0x75cf7a8:
            result = self._tl_userForeign_old2()
        elif constructor == 0xd9ccc4ef:
            result = self._tl_userRequest_old2()
        elif constructor == 0xb29ad7cc:
            result = self._tl_userDeleted_old()
        elif constructor == 0xd10d979a:
            result = self._tl_user_layer65()
        elif constructor == 0x22e49072:
            result = self._tl_user_old()
        elif constructor == 0x7007b451:
            result = self._tl_userSelf_old2()
        assert (result is not None), "constructor hex={0}, int={1} not defined".format(hex(constructor), constructor)
        return result

    def _tl_chatForbidden_old(self):
        constructor = 0xfb0ccc41
        params = Map()
        params.id = self.read_int32
        params.title = self.read_string
        date = self.read_int32
        params.date = self.time_from_ts(date)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_chat_old2(self):
        constructor = 0x7312bc48
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.creator = (flags & 1) != 0
        params.kicked = (flags & 2) != 0
        params.left = (flags & 4) != 0
        params.admins_enabled = (flags & 8) != 0
        params.admin = (flags & 16) != 0
        params.deactivated = (flags & 32) != 0
        params.id = self.read_int32
        params.title = self.read_string
        params.photo = self.chat_photo_deserialize(self.read_int32)
        params.participants_count = self.read_int32
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.version = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_channelForbidden(self):
        constructor = 0x289da732
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.broadcast = (flags & 32) != 0
        params.megagroup = (flags & 256) != 0
        params.id = self.read_int32
        params.access_hash = self.read_int64
        params.title = self.read_string
        if (flags & 65536) != 0:
            until_date = self.read_int32
            params.until_date = self.time_from_ts(until_date)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_channelForbidden_layer67(self):
        constructor = 0x8537784f
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.broadcast = (flags & 32) != 0
        params.megagroup = (flags & 256) != 0
        params.id = self.read_int32
        params.access_hash = self.read_int64
        params.title = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_channel_layer48(self):
        constructor = 0x4b1b7506
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.creator = (flags & 1) != 0
        params.kicked = (flags & 2) != 0
        params.left = (flags & 4) != 0
        params.moderator = (flags & 16) != 0
        params.broadcast = (flags & 32) != 0
        params.verified = (flags & 128) != 0
        params.megagroup = (flags & 256) != 0
        params.restricted = (flags & 512) != 0
        params.democracy = (flags & 1024) != 0
        params.signatures = (flags & 2048) != 0
        params.id = self.read_int32
        params.access_hash = self.read_int64
        params.title = self.read_string
        if (flags & 64) != 0:
            params.username = self.read_string
            params.photo = self.chat_photo_deserialize(self.read_int32)
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.version = self.read_int32
        if (flags & 512) != 0:
            params.restriction_reason = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_geoChat(self):
        constructor = 0x75eaea5a
        params = Map()
        params.id = self.read_int32
        params.access_hash = self.read_int64
        params.title = self.read_string
        params.address = self.read_string
        params.venue = self.read_string
        params.geo = self.geo_point_deserialize(self.read_int32)
        params.photo = self.chat_photo_deserialize(self.read_int32)
        params.participants_count = self.read_int32
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.checked_in = self.read_bool
        params.version = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_channelForbidden_layer52(self):
        constructor = 0x2d85832c
        params = Map()
        params.id = self.read_int32
        params.access_hash = self.read_int64
        params.title = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_chatForbidden(self):
        constructor = 0x7328bdb
        params = Map()
        params.id = self.read_int32
        params.title = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_channel_layer67(self):
        constructor = 0xa14dca52
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.creator = (flags & 1) != 0
        params.kicked = (flags & 2) != 0
        params.left = (flags & 4) != 0
        params.moderator = (flags & 16) != 0
        params.broadcast = (flags & 32) != 0
        params.verified = (flags & 128) != 0
        params.megagroup = (flags & 256) != 0
        params.restricted = (flags & 512) != 0
        params.democracy = (flags & 1024) != 0
        params.signatures = (flags & 2048) != 0
        params.min = (flags & 4096) != 0
        params.id = self.read_int32
        if (flags & 8192) != 0:
            params.access_hash = self.read_int64
        params.title = self.read_string
        if (flags & 64) != 0:
            params.username = self.read_string
        params.photo = self.chat_photo_deserialize(self.read_int32)
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.version = self.read_int32
        if (flags & 512) != 0:
            params.restriction_reason = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def chat_deserialize(self, constructor):
        result = None
        if constructor == 0xfb0ccc41:
            result = self._tl_chatForbidden_old()
        elif constructor == 0x7312bc48:
            result = self._tl_chat_old2()
        elif constructor == 0x289da732:
            result = self._tl_channelForbidden()
        elif constructor == 0x8537784f:
            result = self._tl_channelForbidden_layer67()
        elif constructor == 0x4b1b7506:
            result = self._tl_channel_layer48()
        elif constructor == 0x75eaea5a:
            result = self._tl_geoChat()
        elif constructor == 0x2d85832c:
            result = self._tl_channelForbidden_layer52()
        elif constructor == 0x7328bdb:
            result = self._tl_chatForbidden()
        elif constructor == 0xa14dca52:
            result = self._tl_channel_layer67()
        elif constructor == 0x678e9587:
            result = self._tl_channel_old()
        elif constructor == 0x6e9c9bc7:
            result = self._tl_chat_old()
        elif constructor == 0x9ba2d800:
            result = self._tl_chatEmpty()
        elif constructor == 0xcb44b1c:
            result = self._tl_channel_layer72()
        elif constructor == 0xd91cdd54:
            result = self._tl_chat_layer92()
        elif constructor == 0x3bda1bde:
            result = self._tl_chat()
        elif constructor == 0x4df30834:
            result = self._tl_channel()
        elif constructor == 0x450b7115:
            result = self._tl_channel_layer77()
        elif constructor == 0xc88974ac:
            result = self._tl_channel_layer92()
        assert (result is not None), "constructor hex={0}, int={1} not defined".format(hex(constructor), constructor)
        return result

    def _tl_message_secret(self):
        constructor = 0x555555fa
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.unread = (flags & 1) != 0
        params.out = (flags & 2) != 0
        params.mentioned = (flags & 16) != 0
        params.media_unread = (flags & 32) != 0
        params.id = self.read_int32
        params.ttl = self.read_int32
        params.from_id = self.read_int32
        params.to_id = self.peer_deserialize(self.read_int32)
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.message = self.read_string
        params.media = self.message_media_deserialize(self.read_int32)
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        entities = list()
        for i in range(0, count):
            obj = self.message_entity_deserialize(self.read_int32)
            if obj is None:
                return
            entities.append(obj)
        params.entities = entities
        if (flags & 2048) != 0:
            params.via_bot_name = self.read_string
        if (flags & 8) != 0:
            params.reply_to_random_id = self.read_int64
        if (flags & 131072) != 0:
            params.grouped_id = self.read_int64
        if params.id < 0 or (params.media is not None
                             and ('_tl_messageMediaEmpty' not in self.instances)
                             and ('_tl_messageMediaWebPage' not in self.instances)
                             and params.message is not None
                             and len(params.message) != 0
                             and params.message.startswith("-1")):
            params.attachPath = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_message_secret_layer72(self):
        constructor = 0x555555f9
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.unread = (flags & 1) != 0
        params.out = (flags & 2) != 0
        params.mentioned = (flags & 16) != 0
        params.media_unread = (flags & 32) != 0
        params.id = self.read_int32
        params.ttl = self.read_int32
        params.from_id = self.read_int32
        params.to_id = self.peer_deserialize(self.read_int32)
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.message = self.read_string
        params.media = self.message_media_deserialize(self.read_int32)
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        entities = list()
        for i in range(0, count):
            obj = self.message_entity_deserialize(self.read_int32)
            if obj is None:
                return
            entities.append(obj)
        params.entities = entities
        if (flags & 2048) != 0:
            params.via_bot_name = self.read_string
        if (flags & 8) != 0:
            params.reply_to_random_id = self.read_int64
        if params.id < 0 or (params.media is not None
                             and ('_tl_messageMediaEmpty' not in self.instances)
                             and ('_tl_messageMediaWebPage' not in self.instances)
                             and params.message is not None
                             and len(params.message) != 0
                             and params.message.startswith("-1")):
            params.attachPath = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_message_layer72(self):
        constructor = 0x90dddc11
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.unread = (flags & 1) != 0
        params.out = (flags & 2) != 0
        params.mentioned = (flags & 16) != 0
        params.media_unread = (flags & 32) != 0
        params.silent = (flags & 8192) != 0
        params.post = (flags & 16384) != 0
        params.with_my_score = (flags & 1073741824) != 0
        params.id = self.read_int32
        if (flags & 256) != 0:
            params.from_id = self.read_int32
        params.to_id = self.peer_deserialize(self.read_int32)
        if params.from_id == 0:
            if params.to_id.user_id != 0:
                params.from_id = params.to_id.user_id
            else:
                params.from_id = -params.to_id.channel_id
        if (flags & 4) != 0:
            params.fwd_from = self.message_fwd_header_deserialize(self.read_int32)
        if (flags & 2048) != 0:
            params.via_bot_id = self.read_int32
        if (flags & 8) != 0:
            params.reply_to_msg_id = self.read_int32
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.message = self.read_string
        if (flags & 512) != 0:
            params.media = self.message_media_deserialize(self.read_int32)
        else:
            params.media = self._tl_messageMediaEmpty()
        if (flags & 64) != 0:
            params.reply_markup = self.reply_markup_deserialize(self.read_int32)
        if (flags & 128) != 0:
            magic = self.read_int32
            assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
            count = self.read_int32
            entities = list()
            for i in range(0, count):
                obj = self.message_entity_deserialize(self.read_int32)
                if obj is None:
                    return
                entities.append(obj)
            params.entities = entities
        if (flags & 1024) != 0:
            params.views = self.read_int32
        if (flags & 32768) != 0:
            edit_date = self.read_int32
            params.edit_date = self.time_from_ts(edit_date)
        if (flags & 65536) != 0:
            params.author = self.read_string
        if params.id < 0 or (params.media is not None
                             and ('_tl_messageMediaEmpty' not in self.instances)
                             and ('_tl_messageMediaWebPage' not in self.instances)
                             and params.message is not None
                             and len(params.message) != 0
                             and params.message.startswith("-1")):
            params.attachPath = self.read_string
        if (flags & self.MESSAGE_FLAG_FWD) != 0 and params.id < 0:
            params.fwd_msg_id = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_message_layer68(self):
        constructor = 0xc09be45f
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.unread = (flags & 1) != 0
        params.out = (flags & 2) != 0
        params.mentioned = (flags & 16) != 0
        params.media_unread = (flags & 32) != 0
        params.silent = (flags & 8192) != 0
        params.post = (flags & 16384) != 0
        params.with_my_score = (flags & 1073741824) != 0
        params.id = self.read_int32
        if (flags & 256) != 0:
            params.from_id = self.read_int32
        params.to_id = self.peer_deserialize(self.read_int32)
        if params.from_id == 0:
            if params.to_id.user_id != 0:
                params.from_id = params.to_id.user_id
            else:
                params.from_id = -params.to_id.channel_id
        if (flags & 4) != 0:
            params.fwd_from = self.message_fwd_header_deserialize(self.read_int32)
        if (flags & 2048) != 0:
            params.via_bot_id = self.read_int32
        if (flags & 8) != 0:
            params.reply_to_msg_id = self.read_int32
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.message = self.read_string
        if (flags & 512) != 0:
            params.media = self.message_media_deserialize(self.read_int32)
        else:
            params.media = self._tl_messageMediaEmpty()
        if (flags & 64) != 0:
            params.reply_markup = self.reply_markup_deserialize(self.read_int32)
        if (flags & 128) != 0:
            magic = self.read_int32
            assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
            count = self.read_int32
            entities = list()
            for i in range(0, count):
                obj = self.message_entity_deserialize(self.read_int32)
                if obj is None:
                    return
                entities.append(obj)
            params.entities = entities
        if (flags & 1024) != 0:
            params.views = self.read_int32
        if (flags & 32768) != 0:
            edit_date = self.read_int32
            params.edit_date = self.time_from_ts(edit_date)
        if params.id < 0 or (params.media is not None
                             and ('_tl_messageMediaEmpty' not in self.instances)
                             and ('_tl_messageMediaWebPage' not in self.instances)
                             and params.message is not None
                             and len(params.message) != 0
                             and params.message.startswith("-1")):
            params.attachPath = self.read_string
        if (flags & self.MESSAGE_FLAG_FWD) != 0 and params.id < 0:
            params.fwd_msg_id = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageService(self):
        constructor = 0x9e19a1f6
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.unread = (flags & 1) != 0
        params.out = (flags & 2) != 0
        params.mentioned = (flags & 16) != 0
        params.media_unread = (flags & 32) != 0
        params.silent = (flags & 8192) != 0
        params.post = (flags & 16384) != 0
        params.id = self.read_int32
        if (flags & 256) != 0:
            params.from_id = self.read_int32
        params.to_id = self.peer_deserialize(self.read_int32)
        if (flags & 8) != 0:
            params.reply_to_msg_id = self.read_int32
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.action = self.message_action_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_message_old5(self):
        constructor = 0xf07814c8
        params = Map()
        flags = self.read_int32 | self.MESSAGE_FLAG_HAS_FROM_ID | self.MESSAGE_FLAG_HAS_MEDIA
        params.flags = flags
        params.unread = (flags & 1) != 0
        params.out = (flags & 2) != 0
        params.mentioned = (flags & 16) != 0
        params.media_unread = (flags & 32) != 0
        params.id = self.read_int32
        params.from_id = self.read_int32
        params.to_id = self.peer_deserialize(self.read_int32)
        if (flags & 4) != 0:
            params.fwd_from = self._tl_messageFwdHeader()
            params.fwd_from.from_id = self.read_int32
            params.fwd_from.flags |= 1
            params.fwd_from.date = self.read_int32
        if (flags & 8) != 0:
            params.reply_to_msg_id = self.read_int32
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.message = self.read_string
        params.media = self.message_media_deserialize(self.read_int32)
        if (flags & 64) != 0:
            params.reply_markup = self.reply_markup_deserialize(self.read_int32)
        if (flags & 128) != 0:
            magic = self.read_int32
            assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
            count = self.read_int32
            entities = list()
            for i in range(0, count):
                obj = self.message_entity_deserialize(self.read_int32)
                if obj is None:
                    return
                entities.append(obj)
            params.entities = entities
        if params.id < 0 or (params.media is not None
                             and ('_tl_messageMediaEmpty' not in self.instances)
                             and ('_tl_messageMediaWebPage' not in self.instances)
                             and params.message is not None
                             and len(params.message) != 0
                             and params.message.startswith("-1")):
            params.attachPath = self.read_string
        if (flags & self.MESSAGE_FLAG_FWD) != 0 and params.id < 0:
            params.fwd_msg_id = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageService_old2(self):
        constructor = 0x1d86f70e
        params = Map()
        flags = self.read_int32
        params.unread = (flags & 1) != 0
        params.out = (flags & 2) != 0
        params.mentioned = (flags & 16) != 0
        params.media_unread = (flags & 32) != 0
        params.id = self.read_int32
        params.from_id = self.read_int32
        params.to_id = self.peer_deserialize(self.read_int32)
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.action = self.message_action_deserialize(self.read_int32)
        flags |= self.MESSAGE_FLAG_HAS_FROM_ID
        params.flags = flags
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_message_old3(self):
        constructor = 0xa7ab1991
        params = Map()
        flags = self.read_int32 | self.MESSAGE_FLAG_HAS_FROM_ID | self.MESSAGE_FLAG_HAS_MEDIA
        params.flags = flags
        params.unread = (flags & 1) != 0
        params.out = (flags & 2) != 0
        params.mentioned = (flags & 16) != 0
        params.media_unread = (flags & 32) != 0
        params.id = self.read_int32
        params.from_id = self.read_int32
        params.to_id = self.peer_deserialize(self.read_int32)
        if (flags & 4) != 0:
            params.fwd_from = self._tl_messageFwdHeader()
            params.fwd_from.from_id = self.read_int32
            params.fwd_from.flags |= 1
            params.fwd_from.date = self.read_int32
        if (flags & 8) != 0:
            params.reply_to_msg_id = self.read_int32
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.message = self.read_string
        params.media = self.message_media_deserialize(self.read_int32)
        if params.id < 0 or (params.media is not None
                             and ('_tl_messageMediaEmpty' not in self.instances)
                             and ('_tl_messageMediaWebPage' not in self.instances)
                             and params.message is not None
                             and len(params.message) != 0
                             and params.message.startswith("-1")):
            params.attachPath = self.read_string
        if (flags & self.MESSAGE_FLAG_FWD) != 0 and params.id < 0:
            params.fwd_msg_id = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_message_old4(self):
        constructor = 0xc3060325
        params = Map()
        flags = self.read_int32 | self.MESSAGE_FLAG_HAS_FROM_ID | self.MESSAGE_FLAG_HAS_MEDIA
        params.flags = flags
        params.unread = (flags & 1) != 0
        params.out = (flags & 2) != 0
        params.mentioned = (flags & 16) != 0
        params.media_unread = (flags & 32) != 0
        params.id = self.read_int32
        params.from_id = self.read_int32
        params.to_id = self.peer_deserialize(self.read_int32)
        if (flags & 4) != 0:
            params.fwd_from = self._tl_messageFwdHeader()
            params.fwd_from.from_id = self.read_int32
            params.fwd_from.flags |= 1
            params.fwd_from.date = self.read_int32
        if (flags & 8) != 0:
            params.reply_to_msg_id = self.read_int32
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.message = self.read_string
        params.media = self.message_media_deserialize(self.read_int32)
        if (flags & 64) != 0:
            params.reply_markup = self.reply_markup_deserialize(self.read_int32)
        if params.id < 0 or (params.media is not None
                             and ('_tl_messageMediaEmpty' not in self.instances)
                             and ('_tl_messageMediaWebPage' not in self.instances)
                             and params.message is not None
                             and len(params.message) != 0
                             and params.message.startswith("-1")):
            params.attachPath = self.read_string
        if (flags & self.MESSAGE_FLAG_FWD) != 0 and params.id < 0:
            params.fwd_msg_id = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_message_layer47(self):
        constructor = 0xc992e15c
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.unread = (flags & 1) != 0
        params.out = (flags & 2) != 0
        params.mentioned = (flags & 16) != 0
        params.media_unread = (flags & 32) != 0
        params.id = self.read_int32
        if (flags & 256) != 0:
            params.from_id = self.read_int32
        params.to_id = self.peer_deserialize(self.read_int32)
        if params.from_id == 0:
            if params.to_id.user_id != 0:
                params.from_id = params.to_id.user_id
            else:
                params.from_id = -params.to_id.channel_id
        if (flags & 4) != 0:
            params.fwd_from = self._tl_messageFwdHeader()
            params.peer = self.peer_deserialize(self.read_int32)
            if '_tl_peerChannel' in self.instances:
                params.fwd_from.channel_id = params.peer.channel_id
                params.fwd_from.flags |= 2
            elif '_tl_peerUser' in self.instances:
                params.fwd_from.from_id = params.peer.user_id
                params.fwd_from.flags |= 1
            params.fwd_from.date = self.read_int32
        if (flags & 2048) != 0:
            params.via_bot_id = self.read_int32
        if (flags & 8) != 0:
            params.reply_to_msg_id = self.read_int32
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.message = self.read_string
        if (flags & 512) != 0:
            params.media = self.message_media_deserialize(self.read_int32)
        else:
            params.media = self._tl_messageMediaEmpty()
        if (flags & 64) != 0:
            params.reply_markup = self.reply_markup_deserialize(self.read_int32)
        if (flags & 128) != 0:
            magic = self.read_int32
            assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
            count = self.read_int32
            entities = list()
            for i in range(0, count):
                obj = self.message_entity_deserialize(self.read_int32)
                if obj is None:
                    return
                entities.append(obj)
            params.entities = entities
        if (flags & 1024) != 0:
            params.views = self.read_int32
        if params.id < 0 or (params.media is not None
                             and ('_tl_messageMediaEmpty' not in self.instances)
                             and ('_tl_messageMediaWebPage' not in self.instances)
                             and params.message is not None
                             and len(params.message) != 0
                             and params.message.startswith("-1")):
            params.attachPath = self.read_string
        if (flags & self.MESSAGE_FLAG_FWD) != 0 and params.id < 0:
            params.fwd_msg_id = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_message_old7(self):
        constructor = 0x5ba66c13
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.unread = (flags & 1) != 0
        params.out = (flags & 2) != 0
        params.mentioned = (flags & 16) != 0
        params.media_unread = (flags & 32) != 0
        params.id = self.read_int32
        if (flags & 256) != 0:
            params.from_id = self.read_int32
        params.to_id = self.peer_deserialize(self.read_int32)
        if params.from_id == 0:
            if params.to_id.user_id != 0:
                params.from_id = params.to_id.user_id
            else:
                params.from_id = -params.to_id.channel_id
        if (flags & 4) != 0:
            params.fwd_from = self._tl_messageFwdHeader()
            params.peer = self.peer_deserialize(self.read_int32)
            if '_tl_peerChannel' in self.instances:
                params.fwd_from.channel_id = params.peer.channel_id
                params.fwd_from.flags |= 2
            elif '_tl_peerUser' in self.instances:
                params.fwd_from.from_id = params.peer.user_id
                params.fwd_from.flags |= 1
            params.fwd_from.date = self.read_int32
        if (flags & 8) != 0:
            params.reply_to_msg_id = self.read_int32
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.message = self.read_string
        if (flags & 512) != 0:
            params.media = self.message_media_deserialize(self.read_int32)
        else:
            params.media = self._tl_messageMediaEmpty()
        if (flags & 64) != 0:
            params.reply_markup = self.reply_markup_deserialize(self.read_int32)
        if (flags & 128) != 0:
            magic = self.read_int32
            assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
            count = self.read_int32
            entities = list()
            for i in range(0, count):
                obj = self.message_entity_deserialize(self.read_int32)
                if obj is None:
                    return
                entities.append(obj)
            params.entities = entities
        if (flags & 1024) != 0:
            params.views = self.read_int32
        if params.id < 0 or (params.media is not None
                             and ('_tl_messageMediaEmpty' not in self.instances)
                             and ('_tl_messageMediaWebPage' not in self.instances)
                             and params.message is not None
                             and len(params.message) != 0
                             and params.message.startswith("-1")):
            params.attachPath = self.read_string
        if (flags & self.MESSAGE_FLAG_FWD) != 0 and params.id < 0:
            params.fwd_msg_id = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageService_layer48(self):
        constructor = 0xc06b9607
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.unread = (flags & 1) != 0
        params.out = (flags & 2) != 0
        params.mentioned = (flags & 16) != 0
        params.media_unread = (flags & 32) != 0
        params.silent = (flags & 8192) != 0
        params.post = (flags & 16384) != 0
        params.id = self.read_int32
        if (flags & 256) != 0:
            params.from_id = self.read_int32
        params.to_id = self.peer_deserialize(self.read_int32)
        if params.from_id == 0:
            if params.to_id.user_id != 0:
                params.from_id = params.to_id.user_id
            else:
                params.from_id = -params.to_id.channel_id
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.action = self.message_action_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageEmpty(self):
        constructor = 0x83e5de54
        params = Map()
        params.id = self.read_int32
        params.to_id = self._tl_peerUser()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_message_old6(self):
        constructor = 0x2bebfa86
        params = Map()
        flags = self.read_int32 | self.MESSAGE_FLAG_HAS_FROM_ID
        params.flags = flags
        params.unread = (flags & 1) != 0
        params.out = (flags & 2) != 0
        params.mentioned = (flags & 16) != 0
        params.media_unread = (flags & 32) != 0
        params.id = self.read_int32
        params.from_id = self.read_int32
        params.to_id = self.peer_deserialize(self.read_int32)
        if (flags & 4) != 0:
            params.fwd_from = self._tl_messageFwdHeader()
            params.fwd_from.from_id = self.read_int32
            params.fwd_from.flags |= 1
            params.fwd_from.date = self.read_int32
        if (flags & 8) != 0:
            params.reply_to_msg_id = self.read_int32
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.message = self.read_string
        if (flags & 512) != 0:
            params.media = self.message_media_deserialize(self.read_int32)
        else:
            params.media = self._tl_messageMediaEmpty()
        if (flags & 64) != 0:
            params.reply_markup = self.reply_markup_deserialize(self.read_int32)
        if (flags & 128) != 0:
            magic = self.read_int32
            assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
            count = self.read_int32
            entities = list()
            for i in range(0, count):
                obj = self.message_entity_deserialize(self.read_int32)
                if obj is None:
                    return
                entities.append(obj)
            params.entities = entities
        if params.id < 0 or (params.media is not None
                             and ('_tl_messageMediaEmpty' not in self.instances)
                             and ('_tl_messageMediaWebPage' not in self.instances)
                             and params.message is not None
                             and len(params.message) != 0
                             and params.message.startswith("-1")):
            params.attachPath = self.read_string
        if (flags & self.MESSAGE_FLAG_FWD) != 0 and params.id < 0:
            params.fwd_msg_id = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageForwarded_old2(self):
        constructor = 0xa367e716
        params = Map()
        flags = self.read_int32
        params.unread = (flags & 1) != 0
        params.out = (flags & 2) != 0
        params.mentioned = (flags & 16) != 0
        params.media_unread = (flags & 32) != 0
        params.id = self.read_int32
        params.fwd_from = self._tl_messageFwdHeader()
        params.fwd_from.from_id = self.read_int32
        params.fwd_from.flags |= 1
        params.fwd_from.date = self.read_int32
        params.from_id = self.read_int32
        params.to_id = self.peer_deserialize(self.read_int32)
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.message = self.read_string
        flags |= self.MESSAGE_FLAG_FWD | self.MESSAGE_FLAG_HAS_FROM_ID | self.MESSAGE_FLAG_HAS_MEDIA
        params.flags = flags
        params.media = self.message_media_deserialize(self.read_int32)
        if params.id < 0:
            params.fwd_msg_id = self.read_int32
        if params.id < 0 or (params.media is not None
                             and ('_tl_messageMediaEmpty' not in self.instances)
                             and ('_tl_messageMediaWebPage' not in self.instances)
                             and params.message is not None
                             and len(params.message) != 0
                             and params.message.startswith("-1")):
            params.attachPath = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageForwarded_old(self):  # FIXME May be .flags is wrong: self.read_int32 -> None
        constructor = 0x5f46804
        params = Map()
        flags = self.read_int32
        params.id = self.read_int32
        params.fwd_from = self._tl_messageFwdHeader()
        params.fwd_from.from_id = self.read_int32
        params.fwd_from.flags |= 1
        params.fwd_from.date = self.read_int32
        params.from_id = self.read_int32
        params.to_id = self.peer_deserialize(self.read_int32)
        params.out = self.read_bool
        params.unread = self.read_bool
        flags |= self.MESSAGE_FLAG_FWD | self.MESSAGE_FLAG_HAS_FROM_ID | self.MESSAGE_FLAG_HAS_MEDIA
        params.flags = flags
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.message = self.read_string
        params.media = self.message_media_deserialize(self.read_int32)
        if params.id < 0:
            params.fwd_msg_id = self.read_int32
        if params.id < 0 or (params.media is not None
                             and ('_tl_messageMediaEmpty' not in self.instances)
                             and ('_tl_messageMediaWebPage' not in self.instances)
                             and params.message is not None
                             and len(params.message) != 0
                             and params.message.startswith("-1")):
            params.attachPath = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_message_old2(self):
        constructor = 0x567699b3
        params = Map()
        flags = self.read_int32 | self.MESSAGE_FLAG_HAS_FROM_ID | self.MESSAGE_FLAG_HAS_MEDIA
        params.flags = flags
        params.unread = (flags & 1) != 0
        params.out = (flags & 2) != 0
        params.mentioned = (flags & 16) != 0
        params.media_unread = (flags & 32) != 0
        params.id = self.read_int32
        params.from_id = self.read_int32
        params.to_id = self.peer_deserialize(self.read_int32)
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.message = self.read_string
        params.media = self.message_media_deserialize(self.read_int32)
        if params.id < 0 or (params.media is not None
                             and ('_tl_messageMediaEmpty' not in self.instances)
                             and ('_tl_messageMediaWebPage' not in self.instances)
                             and params.message is not None
                             and len(params.message) != 0
                             and params.message.startswith("-1")):
            params.attachPath = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_messageService_old(self):  # FIXME May be .flags is wrong: self.read_int32 -> None
        constructor = 0x9f8d60bb
        params = Map()
        flags = self.read_int32
        params.id = self.read_int32
        params.from_id = self.read_int32
        params.to_id = self.peer_deserialize(self.read_int32)
        params.out = self.read_bool
        params.unread = self.read_bool
        flags |= self.MESSAGE_FLAG_HAS_FROM_ID
        params.flags = flags
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.action = self.message_action_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_message_old(self):  # FIXME May be .flags is wrong: self.read_int32 -> None
        constructor = 0x22eb6aba
        params = Map()
        flags = self.read_int32
        params.id = self.read_int32
        params.from_id = self.read_int32
        params.to_id = self.peer_deserialize(self.read_int32)
        params.out = self.read_bool
        params.unread = self.read_bool
        flags |= self.MESSAGE_FLAG_HAS_FROM_ID | self.MESSAGE_FLAG_HAS_MEDIA
        params.flags = flags
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.message = self.read_string
        params.media = self.message_media_deserialize(self.read_int32)
        if params.id < 0 or (params.media is not None
                             and ('_tl_messageMediaEmpty' not in self.instances)
                             and ('_tl_messageMediaWebPage' not in self.instances)
                             and params.message is not None
                             and len(params.message) != 0
                             and params.message.startswith("-1")):
            params.attachPath = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_message(self):
        constructor = 0x44f9b43d
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.out = (flags & 2) != 0
        params.mentioned = (flags & 16) != 0
        params.media_unread = (flags & 32) != 0
        params.silent = (flags & 8192) != 0
        params.post = (flags & 16384) != 0
        params.id = self.read_int32
        if (flags & 256) != 0:
            params.from_id = self.read_int32
        params.to_id = self.peer_deserialize(self.read_int32)
        if (flags & 4) != 0:
            params.fwd_from = self.message_fwd_header_deserialize(self.read_int32)
        if (flags & 2048) != 0:
            params.via_bot_id = self.read_int32
        if (flags & 8) != 0:
            params.reply_to_msg_id = self.read_int32
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.message = self.read_string
        if (flags & 512) != 0:
            params.media = self.message_media_deserialize(self.read_int32)
            if params.media:
                ttl = params.media.ttl_seconds
        if (flags & 64) != 0:
            params.reply_markup = self.reply_markup_deserialize(self.read_int32)
        if (flags & 128) != 0:
            magic = self.read_int32
            assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
            count = self.read_int32
            entities = list()
            for i in range(0, count):
                obj = self.message_entity_deserialize(self.read_int32)
                if obj is None:
                    return
                entities.append(obj)
            params.entities = entities
        if (flags & 1024) != 0:
            params.views = self.read_int32
        if (flags & 32768) != 0:
            edit_date = self.read_int32
            params.edit_date = self.time_from_ts(edit_date)
        if (flags & 65536) != 0:
            params.author = self.read_string
        if (flags & 131072) != 0:
            params.grouped_id = self.read_int64
        if params.id < 0 or (params.media is not None
                             and ('_tl_messageMediaEmpty' not in self.instances)
                             and ('_tl_messageMediaWebPage' not in self.instances)
                             and params.message is not None
                             and len(params.message) != 0
                             and params.message.startswith("-1")):
            params.attachPath = self.read_string
        if (flags & self.MESSAGE_FLAG_FWD) != 0 and params.id < 0:
            params.fwd_msg_id = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_message_secret_old(self):
        constructor = 0x555555F8
        params = Map()
        flags = self.read_int32 | self.MESSAGE_FLAG_HAS_FROM_ID | self.MESSAGE_FLAG_HAS_MEDIA
        params.flags = flags
        params.unread = (flags & 1) != 0
        params.out = (flags & 2) != 0
        params.mentioned = (flags & 16) != 0
        params.media_unread = (flags & 32) != 0
        params.id = self.read_int32
        params.ttl = self.read_int32
        params.from_id = self.read_int32
        params.to_id = self.peer_deserialize(self.read_int32)
        date = self.read_int32
        params.date = self.time_from_ts(date)
        params.message = self.read_string
        params.media = self.message_media_deserialize(self.read_int32)
        if params.id < 0 or (params.media is not None
                             and ('_tl_messageMediaEmpty' not in self.instances)
                             and ('_tl_messageMediaWebPage' not in self.instances)
                             and params.message is not None
                             and len(params.message) != 0
                             and params.message.startswith("-1")):
            params.attachPath = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def message_deserialize(self, constructor):
        result = None
        if constructor == 0x1d86f70e:
            result = self._tl_messageService_old2()
        elif constructor == 0xa7ab1991:
            result = self._tl_message_old3()
        elif constructor == 0xc3060325:
            result = self._tl_message_old4()
        elif constructor == 0x555555fa:
            result = self._tl_message_secret()
        elif constructor == 0x555555f9:
            result = self._tl_message_secret_layer72()
        elif constructor == 0x90dddc11:
            result = self._tl_message_layer72()
        elif constructor == 0xc09be45f:
            result = self._tl_message_layer68()
        elif constructor == 0xc992e15c:
            result = self._tl_message_layer47()
        elif constructor == 0x5ba66c13:
            result = self._tl_message_old7()
        elif constructor == 0xc06b9607:
            result = self._tl_messageService_layer48()
        elif constructor == 0x83e5de54:
            result = self._tl_messageEmpty()
        elif constructor == 0x2bebfa86:
            result = self._tl_message_old6()
        elif constructor == 0x44f9b43d:
            result = self._tl_message()
        elif constructor == 0xa367e716:
            result = self._tl_messageForwarded_old2()
        elif constructor == 0x5f46804:
            result = self._tl_messageForwarded_old()
        elif constructor == 0x567699b3:
            result = self._tl_message_old2()
        elif constructor == 0x9f8d60bb:
            result = self._tl_messageService_old()
        elif constructor == 0x22eb6aba:
            result = self._tl_message_old()
        elif constructor == 0x555555F8:
            result = self._tl_message_secret_old()
        elif constructor == 0x9e19a1f6:
            result = self._tl_messageService()
        elif constructor == 0xf07814c8:
            result = self._tl_message_old5()
        assert (result is not None), "constructor hex={0}, int={1} not defined".format(hex(constructor), constructor)
        return result

    def _tl_botInfoEmpty_layer48(self):
        constructor = 0xbb2e37ce
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_botCommand(self):
        constructor = 0xc27ac8c7
        params = Map()
        command = self.read_string
        description = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def bot_command_deserialize(self, constructor):
        assert (constructor == 0xc27ac8c7), "{} asseratation".format(inspect.stack()[0][3])
        result = self._tl_botCommand()
        self.instances.append(inspect.stack()[0][3])
        return result

    def _tl_botInfo(self):
        constructor = 0x98e81d3a
        params = Map()
        params.user_id = self.read_int32
        params.description = self.read_string
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        commands = list()
        for i in range(0, count):
            obj = self.bot_command_deserialize(self.read_int32)
            if obj is None:
                return
            commands.append(obj)
        params.commands = commands
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_botInfo_layer48(self):
        constructor = 0x9cf585d
        params = Map()
        params.user_id = self.read_int32
        params.version = self.read_int32
        params.myvar = self.read_string
        params.description = self.read_string
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        commands = list()
        for i in range(0, count):
            obj = self.bot_command_deserialize(self.read_int32)
            if obj is None:
                return
            commands.append(obj)
        params.commands = commands
        self.instances.append(inspect.stack()[0][3])
        return params

    def bot_info_deserialize(self, constructor):
        result = None
        if constructor == 0xbb2e37ce:
            result = self._tl_botInfoEmpty_layer48()
        elif constructor == 0x98e81d3a:
            result = self. _tl_botInfo()
        elif constructor == 0x9cf585d:
            result = self._tl_botInfo_layer48()
        assert (result is not None), "constructor hex={0}, int={1} not defined".format(hex(constructor), constructor)
        return result

    def _tl_chatParticipantCreator(self):
        constructor = 0xda13538a
        params = Map()
        params.user_id = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_chatParticipant(self):
        constructor = 0xc8d7493e
        params = Map()
        params.user_id = self.read_int32
        params.inviter_id = self.read_int32
        date = self.read_int32
        params.date = self.time_from_ts(date)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_chatParticipantAdmin(self):
        constructor = 0xe2d6e436
        params = Map()
        params.user_id = self.read_int32
        params.inviter_id = self.read_int32
        date = self.read_int32
        params.date = self.time_from_ts(date)
        self.instances.append(inspect.stack()[0][3])
        return params

    def chat_participant_deserialize(self, constructor):
        result = None
        if constructor == 0xc8d7493e:
            result = self._tl_chatParticipant()
        elif constructor == 0xda13538a:
            result = self._tl_chatParticipantCreator()
        elif constructor == 0xe2d6e436:
            result = self._tl_chatParticipantAdmin()
        assert (result is not None), "constructor hex={0}, int={1} not defined".format(hex(constructor), constructor)
        return result

    def _tl_chatParticipantsForbidden(self):
        constructor = 0xfc900c2b
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.chat_id = self.read_int32
        if (flags & 1) != 0:
            params.self_participant = self.chat_participant_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_chatParticipants(self):
        constructor = 0x3f460fed
        params = Map()
        params.chat_id = self.read_int32
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        participants = list()
        for i in range(0, count):
            obj = self.chat_participant_deserialize(self.read_int32)
            if obj is None:
                return
            participants.append(obj)
        params.participants = participants
        params.version = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_chatParticipants_old(self):
        constructor = 0x7841b415
        params = Map()
        params.chat_id = self.read_int32
        params.admin_id = self.read_int32
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        participants = list()
        for i in range(0, count):
            obj = self.chat_participant_deserialize(self.read_int32)
            if obj is None:
                return
            participants.append(obj)
        params.participants = participants
        params.version = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_chatParticipantsForbidden_old(self):
        constructor = 0xfd2bb8a
        params = Map()
        params.chat_id = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def chat_participants_deserialize(self, constructor):
        result = None
        if constructor == 0xfc900c2b:
            result = self._tl_chatParticipantsForbidden()
        elif constructor == 0x3f460fed:
            result = self._tl_chatParticipants()
        elif constructor == 0x7841b415:
            result = self._tl_chatParticipants_old()
        elif constructor == 0xfd2bb8a:
            result = self._tl_chatParticipantsForbidden_old()
        assert (result is not None), "constructor hex={0}, int={1} not defined".format(hex(constructor), constructor)
        return result

    def _tl_peerNotifySettings_layer77(self):
        constructor = 0x9acda4c0
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.show_previews = (flags & 1) != 0
        params.silent = (flags & 2) != 0
        params.mute_until = self.read_int32
        params.sound = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_peerNotifySettings_layer47(self):
        constructor = 0x8d5e11ee
        params = Map()
        params.mute_until = self.read_int32
        params.sound = self.read_string
        params.show_previews = self.read_bool
        params.events_mask = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_peerNotifySettings(self):
        constructor = 0xaf509d20
        params = Map()
        flags = self.read_int32
        params.flags = flags
        if (flags & 1) != 0:
            show_previews = self.read_bool
        if (flags & 2) != 0:
            silent = self.read_bool
        if (flags & 4) != 0:
            mute_until = self.read_int32
        if (flags & 8) != 0:
            sound = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_peerNotifySettingsEmpty(self):
        constructor = 0x70a68512
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def peer_notify_settings_deserialize(self, constructor):
        result = None
        if constructor == 0x9acda4c0:
            result = self._tl_peerNotifySettings_layer77()
        elif constructor == 0xaf509d20:
            result = self._tl_peerNotifySettings()
        elif constructor == 0x8d5e11ee:
            result = self._tl_peerNotifySettings_layer47()
        elif constructor == 0x70a68512:
            result = self._tl_peerNotifySettingsEmpty()
        assert (result is not None), "constructor hex={0}, int={1} not defined".format(hex(constructor), constructor)
        return result

    def _tl_chatInviteEmpty(self):
        constructor = 0x69df3769
        params = Map()
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_chatInviteExported(self):
        constructor = 0xfc2e05bc
        params = Map()
        params.link = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def exported_chat_invite_deserialize(self, constructor):
        result = None
        if constructor == 0xfc2e05bc:
            result = self._tl_chatInviteExported()
        elif constructor == 0x69df3769:
            result = self._tl_chatInviteEmpty()
        assert (result is not None), "constructor hex={0}, int={1} not defined".format(hex(constructor), constructor)
        return result

    def _tl_stickerSet_old(self):
        constructor = 0xa7a43b17
        params = Map()
        params.id = self.read_int64
        params.access_hash = self.read_int64
        params.title = self.read_string
        params.short_name = self.read_string
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_stickerSet(self):
        constructor = 0xcd303b41
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.installed = (flags & 1) != 0
        params.archived = (flags & 2) != 0
        params.official = (flags & 4) != 0
        params.masks = (flags & 8) != 0
        params.id = self.read_int64
        params.access_hash = self.read_int64
        params.title = self.read_string
        params.short_name = self.read_string
        params.count = self.read_int32
        params.hash = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def sticker_set_deserialize(self, constructor):
        result = None
        if constructor == 0xa7a43b17:
            result = self._tl_stickerSet_old()
        elif constructor == 0xcd303b41:
            result = self._tl_stickerSet()
        assert (result is not None), "constructor hex={0}, int={1} not defined".format(hex(constructor), constructor)
        return result

    def _tl_chatFull(self):
        constructor = 0x1b7c9db3
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.can_set_username = (flags & 128) != 0
        params.id = self.read_int32
        params.about = self.read_string
        params.participants = self.chat_participants_deserialize(self.read_int32)
        if (flags & 4) != 0:
            params.chat_photo = self.photo_deserialize(self.read_int32)
        params.notify_settings = self.peer_notify_settings_deserialize(self.read_int32)
        params.exported_invite = self.exported_chat_invite_deserialize(self.read_int32)
        if (flags & 8) != 0:
            magic = self.read_int32
            assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
            count = self.read_int32
            bot_info = list()
            for i in range(0, count):
                obj = self.bot_info_deserialize(self.read_int32)
                if obj is None:
                    return
                bot_info.append(obj)
            params.bot_info = bot_info
        if (flags & 64) != 0:
            params.pinned_msg_id = self.read_int32
        if (flags & 2048) != 0:
            params.folder_id = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_chatFull_layer87(self):
        constructor = 0x2e02a614
        params = Map()
        params.id = self.read_int32
        params.participants = self.chat_participants_deserialize(self.read_int32)
        params.chat_photo = self.photo_deserialize(self.read_int32)
        params.notify_settings = self.peer_notify_settings_deserialize(self.read_int32)
        params.exported_invite = self.exported_chat_invite_deserialize(self.read_int32)
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        bot_info = list()
        for i in range(0, count):
            obj = self.bot_info_deserialize(self.read_int32)
            if obj is None:
                return
            bot_info.append(obj)
        params.bot_info = bot_info
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_channelFull_layer67(self):
        constructor = 0xc3d5512f
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.can_view_participants = (flags & 8) != 0
        params.can_set_username = (flags & 64) != 0
        params.id = self.read_int32
        params.about = self.read_string
        if (flags & 1) != 0:
            params.participants_count = self.read_int32
        if (flags & 2) != 0:
            params.admins_count = self.read_int32
        if (flags & 4) != 0:
            params.kicked_count = self.read_int32
        params.read_inbox_max_id = self.read_int32
        params.read_outbox_max_id = self.read_int32
        params.unread_count = self.read_int32
        params.chat_photo = self.photo_deserialize(self.read_int32)
        params.notify_settings = self.peer_notify_settings_deserialize(self.read_int32)
        params.exported_invite = self.exported_chat_invite_deserialize(self.read_int32)
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        bot_info = list()
        for i in range(0, count):
            obj = self.bot_info_deserialize(self.read_int32)
            if obj is None:
                return
            bot_info.append(obj)
        params.bot_info = bot_info
        if (flags & 16) != 0:
            params.migrated_from_chat_id = self.read_int32
        if (flags & 16) != 0:
            params.migrated_from_max_id = self.read_int32
        if (flags & 32) != 0:
            params.pinned_msg_id = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_channelFull_layer70(self):
        constructor = 0x95cb5f57
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.can_view_participants = (flags & 8) != 0
        params.can_set_username = (flags & 64) != 0
        params.id = self.read_int32
        params.about = self.read_string
        if (flags & 1) != 0:
            params.participants_count = self.read_int32
        if (flags & 2) != 0:
            params.admins_count = self.read_int32
        if (flags & 4) != 0:
            params.kicked_count = self.read_int32
        if (flags & 4) != 0:
            params.banned_count = self.read_int32
        params.read_inbox_max_id = self.read_int32
        params.read_outbox_max_id = self.read_int32
        params.unread_count = self.read_int32
        params.chat_photo = self.photo_deserialize(self.read_int32)
        params.notify_settings = self.peer_notify_settings_deserialize(self.read_int32)
        params.exported_invite = self.exported_chat_invite_deserialize(self.read_int32)
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        bot_info = list()
        for i in range(0, count):
            obj = self.bot_info_deserialize(self.read_int32)
            if obj is None:
                return
            bot_info.append(obj)
        params.bot_info = bot_info
        if (flags & 16) != 0:
            params.migrated_from_chat_id = self.read_int32
        if (flags & 16) != 0:
            params.migrated_from_max_id = self.read_int32
        if (flags & 32) != 0:
            params.pinned_msg_id = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_channelFull_layer71(self):
        constructor = 0x17f45fcf
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.can_view_participants = (flags & 8) != 0
        params.can_set_username = (flags & 64) != 0
        params.can_set_stickers = (flags & 128) != 0
        params.id = self.read_int32
        params.about = self.read_string
        if (flags & 1) != 0:
            params.participants_count = self.read_int32
        if (flags & 2) != 0:
            params.admins_count = self.read_int32
        if (flags & 4) != 0:
            params.kicked_count = self.read_int32
        if (flags & 4) != 0:
            params.banned_count = self.read_int32
        params.read_inbox_max_id = self.read_int32
        params.read_outbox_max_id = self.read_int32
        params.unread_count = self.read_int32
        params.chat_photo = self.photo_deserialize(self.read_int32)
        params.notify_settings = self.peer_notify_settings_deserialize(self.read_int32)
        params.exported_invite = self.exported_chat_invite_deserialize(self.read_int32)
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        bot_info = list()
        for i in range(0, count):
            obj = self.bot_info_deserialize(self.read_int32)
            if obj is None:
                return
            bot_info.append(obj)
        params.bot_info = bot_info
        if (flags & 16) != 0:
            params.migrated_from_chat_id = self.read_int32
        if (flags & 16) != 0:
            params.migrated_from_max_id = self.read_int32
        if (flags & 32) != 0:
            params.pinned_msg_id = self.read_int32
        if (flags & 256) != 0:
            params.stickerset = self.sticker_set_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_channelFull_layer72(self):
        constructor = 0x76af5481
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.can_view_participants = (flags & 8) != 0
        params.can_set_username = (flags & 64) != 0
        params.can_set_stickers = (flags & 128) != 0
        params.hidden_prehistory = (flags & 1024) != 0
        params.id = self.read_int32
        params.about = self.read_string
        if (flags & 1) != 0:
            params.participants_count = self.read_int32
        if (flags & 2) != 0:
            params.admins_count = self.read_int32
        if (flags & 4) != 0:
            params.kicked_count = self.read_int32
        if (flags & 4) != 0:
            params.banned_count = self.read_int32
        params.read_inbox_max_id = self.read_int32
        params.read_outbox_max_id = self.read_int32
        params.unread_count = self.read_int32
        params.chat_photo = self.photo_deserialize(self.read_int32)
        params.notify_settings = self.peer_notify_settings_deserialize(self.read_int32)
        params.exported_invite = self.exported_chat_invite_deserialize(self.read_int32)
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        bot_info = list()
        for i in range(0, count):
            obj = self.bot_info_deserialize(self.read_int32)
            if obj is None:
                return
            bot_info.append(obj)
        params.bot_info = bot_info
        if (flags & 16) != 0:
            params.migrated_from_chat_id = self.read_int32
        if (flags & 16) != 0:
            params.migrated_from_max_id = self.read_int32
        if (flags & 32) != 0:
            params.pinned_msg_id = self.read_int32
        if (flags & 256) != 0:
            params.stickerset = self.sticker_set_deserialize(self.read_int32)
        if (flags & 512) != 0:
            params.available_min_id = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_channelFull_layer89(self):
        constructor = 0xcbb62890
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.can_view_participants = (flags & 8) != 0
        params.can_set_username = (flags & 64) != 0
        params.can_set_stickers = (flags & 128) != 0
        params.hidden_prehistory = (flags & 1024) != 0
        params.id = self.read_int32
        params.about = self.read_string
        if (flags & 1) != 0:
            params.participants_count = self.read_int32
        if (flags & 2) != 0:
            params.admins_count = self.read_int32
        if (flags & 4) != 0:
            params.kicked_count = self.read_int32
        if (flags & 4) != 0:
            params.banned_count = self.read_int32
        params.read_inbox_max_id = self.read_int32
        params.read_outbox_max_id = self.read_int32
        params.unread_count = self.read_int32
        params.chat_photo = self.photo_deserialize(self.read_int32)
        params.notify_settings = self.peer_notify_settings_deserialize(self.read_int32)
        params.exported_invite = self.exported_chat_invite_deserialize(self.read_int32)
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        bot_info = list()
        for i in range(0, count):
            obj = self.bot_info_deserialize(self.read_int32)
            if obj is None:
                return
            bot_info.append(obj)
        params.bot_info = bot_info
        if (flags & 16) != 0:
            params.migrated_from_chat_id = self.read_int32
        if (flags & 16) != 0:
            params.migrated_from_max_id = self.read_int32
        if (flags & 32) != 0:
            params.pinned_msg_id = self.read_int32
        if (flags & 256) != 0:
            params.stickerset = self.sticker_set_deserialize(self.read_int32)
        if (flags & 512) != 0:
            params.available_min_id = self.read_int32
        if (flags & 2048) != 0:
            params.call_msg_id = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_channelFull(self):
        constructor = 0x9882e516
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.can_view_participants = (flags & 8) != 0
        params.can_set_username = (flags & 64) != 0
        params.can_set_stickers = (flags & 128) != 0
        params.hidden_prehistory = (flags & 1024) != 0
        params.can_view_stats = (flags & 4096) != 0
        params.id = self.read_int32
        params.about = self.read_string
        if (flags & 1) != 0:
            params.participants_count = self.read_int32
        if (flags & 2) != 0:
            params.admins_count = self.read_int32
        if (flags & 4) != 0:
            params.kicked_count = self.read_int32
        if (flags & 4) != 0:
            params.banned_count = self.read_int32
        if (flags & 8192) != 0:
            params.online_count = self.read_int32
        params.read_inbox_max_id = self.read_int32
        params.read_outbox_max_id = self.read_int32
        params.unread_count = self.read_int32
        params.chat_photo = self.photo_deserialize(self.read_int32)
        params.notify_settings = self.peer_notify_settings_deserialize(self.read_int32)
        params.exported_invite = self.exported_chat_invite_deserialize(self.read_int32)
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        bot_info = list()
        for i in range(0, count):
            obj = self.bot_info_deserialize(self.read_int32)
            if obj is None:
                return
            bot_info.append(obj)
        params.bot_info = bot_info
        if (flags & 16) != 0:
            params.migrated_from_chat_id = self.read_int32
        if (flags & 16) != 0:
            params.migrated_from_max_id = self.read_int32
        if (flags & 32) != 0:
            params.pinned_msg_id = self.read_int32
        if (flags & 256) != 0:
            params.stickerset = self.sticker_set_deserialize(self.read_int32)
        if (flags & 512) != 0:
            params.available_min_id = self.read_int32
        if (flags & 2048) != 0:
            params.call_msg_id = self.read_int32
        if (flags & 8192) != 0:
            params.linked_chat_id = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_channelFull_layer52(self):
        constructor = 0x97bee562
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.can_view_participants = (flags & 8) != 0
        params.can_set_username = (flags & 64) != 0
        params.id = self.read_int32
        params.about = self.read_string
        if (flags & 1) != 0:
            params.participants_count = self.read_int32
        if (flags & 2) != 0:
            params.admins_count = self.read_int32
        if (flags & 4) != 0:
            params.kicked_count = self.read_int32
        params.read_inbox_max_id = self.read_int32
        params.unread_count = self.read_int32
        params.unread_important_count = self.read_int32
        params.chat_photo = self.photo_deserialize(self.read_int32)
        params.notify_settings = self.peer_notify_settings_deserialize(self.read_int32)
        params.exported_invite = self.exported_chat_invite_deserialize(self.read_int32)
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        bot_info = list()
        for i in range(0, count):
            obj = self.bot_info_deserialize(self.read_int32)
            if obj is None:
                return
            bot_info.append(obj)
        params.bot_info = bot_info
        if (flags & 16) != 0:
            params.migrated_from_chat_id = self.read_int32
        if (flags & 16) != 0:
            params.migrated_from_max_id = self.read_int32
        if (flags & 32) != 0:
            params.pinned_msg_id = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_channelFull_layer48(self):
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.can_view_participants = (flags & 8) != 0
        params.id = self.read_int32
        params.about = self.read_string
        if (flags & 1) != 0:
            params.participants_count = self.read_int32
        if (flags & 2) != 0:
            params.admins_count = self.read_int32
        if (flags & 4) != 0:
            params.kicked_count = self.read_int32
        params.read_inbox_max_id = self.read_int32
        params.unread_count = self.read_int32
        params.unread_important_count = self.read_int32
        params.chat_photo = self.photo_deserialize(self.read_int32)
        params.notify_settings = self.peer_notify_settings_deserialize(self.read_int32)
        params.exported_invite = self.exported_chat_invite_deserialize(self.read_int32)
        magic = self.read_int32
        assert (magic == 0x1cb5c415), "magic in {}".format(inspect.stack()[0][3])
        count = self.read_int32
        bot_info = list()
        for i in range(0, count):
            obj = self.bot_info_deserialize(self.read_int32)
            if obj is None:
                return
            bot_info.append(obj)
        params.bot_info = bot_info
        if (flags & 16) != 0:
            params.migrated_from_chat_id = self.read_int32
        if (flags & 16) != 0:
            params.migrated_from_max_id = self.read_int32
        self.instances.append(inspect.stack()[0][3])
        return params

    def _tl_channelFull_old(self):
        constructor = 0xfab31aa3
        params = Map()
        flags = self.read_int32
        params.flags = flags
        params.can_view_participants = (flags & 8) != 0
        params.id = self.read_int32
        params.about = self.read_string
        if (flags & 1) != 0:
            params.participants_count = self.read_int32
        if (flags & 2) != 0:
            params.admins_count = self.read_int32
        if (flags & 4) != 0:
            params.kicked_count = self.read_int32
        params.read_inbox_max_id = self.read_int32
        params.unread_count = self.read_int32
        params.unread_important_count = self.read_int32
        params.chat_photo = self.photo_deserialize(self.read_int32)
        params.notify_settings = self.peer_notify_settings_deserialize(self.read_int32)
        params.exported_invite = self.exported_chat_invite_deserialize(self.read_int32)
        self.instances.append(inspect.stack()[0][3])
        return params

    def chat_full_deserialize(self, constructor):
        result = None
        if constructor == 0x1b7c9db3:
            result = self._tl_chatFull()
        elif constructor == 0x22a235da:
            result = self._tl_chatFull_layer98()
        elif constructor == 0xedd2a791:
            result = self._tl_chatFull_layer92()
        elif constructor == 0x2e02a614:
            result = self._tl_chatFull_layer87()
        elif constructor == 0x9882e516:
            result = self._tl_channelFull()
        elif constructor == 0x1c87a71a:
            result = self._tl_channelFull_layer98()
        elif constructor == 0x3648977:
            result = self._tl_channelFull_layer99()
        elif constructor == 0xcbb62890:
            result = self._tl_channelFull_layer89()
        elif constructor == 0x17f45fcf:
            result = self._tl_channelFull_layer71()
        elif constructor == 0x76af5481:
            result = self._tl_channelFull_layer72()
        elif constructor == 0x95cb5f57:
            result = self._tl_channelFull_layer70()
        elif constructor == 0x97bee562:
            result = self._tl_channelFull_layer52()
        elif constructor == 0xc3d5512f:
            result = self._tl_channelFull_layer67()
        elif constructor == 0x9e341ddf:
            result = self._tl_channelFull_layer48()
        elif constructor == 0xfab31aa3:
            result = self._tl_channelFull_old()
        assert (result is not None), "constructor hex={0}, int={1} not defined".format(hex(constructor), constructor)
        return result
