#/*___wenyan_module_易經_start___*/
# -*- coding: utf-8 -*-
class Ctnr:
  def __init__(self):self.dict = dict();self.length = 0;self.it = -1;
  def push(self,*args):
    for arg in args:
      self.dict[str(self.length)]=arg; self.length+=1
  def __getitem__(self,i):
    try: return self.dict[str(i)]
    except: return None
  def __setitem__(self,i,x):
    self.dict[str(i)]=x
    inti = None
    try:
      inti = int(i)
      if (abs(inti - float(i))>0.0001): inti=None
    except: pass
    if (inti != None):
      self.length=inti+1
      for j in range(0,self.length):
        try:  self.dict[str(j)]
        except: self.dict[str(j)]=None
  def slice(self,i):
    ret = Ctnr();
    for i in range(i,self.length): ret.push(self[i])
    return ret
  def concat(self,other):
    ret = Ctnr();
    for i in range(0,self.length): ret.push(self[i])
    for i in range(0,other.length): ret.push(other[i])
    return ret
  def __str__(self):
    if (len(self.dict.keys())==self.length):
      ret = "["
      for k in range(0,self.length):
        v = self[k]
        if (isinstance(v,Ctnr)): ret += v.__str__()
        else: ret += str(v)
        ret+=","
      ret += "]"
      return ret;
    else:
      ret = "{"
      for k in self.dict.keys():
        ret += str(k)+":"
        v = self.dict[k]
        if (isinstance(v,Ctnr)): ret += v.__str__()
        else: ret += str(v)
        ret+=","
      ret += "}"
      return ret;
  def __repr__(self):
    return self.__str__()
  def __iter__(self):
    self.it = -1;
    return self
  def __next__(self):
    self.it += 1
    if (self.it >= self.length): raise StopIteration()
    return self[self.it]
globals()['Ctnr']=Ctnr;
class JSON:
  @staticmethod
  def stringify(x):
    return x;
#####
運數=42
運=lambda _:0
def 運 (甲):
	global 運數;
	global 運;
	""" "運者。隨機種子也" """

	運數=甲;

占=lambda _:0
def 占():
	global 運數;
	global 運;
	global 占;
	""" "線性同餘方法所得隨機數也" """
	模=4294967296
	""" "有數二千二百六十九萬五千四百七十七。名之曰「倍」。" """
	上倍=22675456
	下倍=20021
	增=1
	_ans1=運數*上倍;
	_ans2=_ans1%模;

	上餘=_ans2;
	_ans3=運數*下倍;
	_ans4=上餘+_ans3;
	_ans5=_ans4+增;
	_ans6=_ans5%模;

	運數=_ans6;
	_ans7=運數/模;

	卦=_ans7;
	return 卦


#/*___wenyan_module_易經_end___*/
#/*___wenyan_module_算經_start___*/
# -*- coding: utf-8 -*-
class Ctnr:
  def __init__(self):self.dict = dict();self.length = 0;self.it = -1;
  def push(self,*args):
    for arg in args:
      self.dict[str(self.length)]=arg; self.length+=1
  def __getitem__(self,i):
    try: return self.dict[str(i)]
    except: return None
  def __setitem__(self,i,x):
    self.dict[str(i)]=x
    inti = None
    try:
      inti = int(i)
      if (abs(inti - float(i))>0.0001): inti=None
    except: pass
    if (inti != None):
      self.length=inti+1
      for j in range(0,self.length):
        try:  self.dict[str(j)]
        except: self.dict[str(j)]=None
  def slice(self,i):
    ret = Ctnr();
    for i in range(i,self.length): ret.push(self[i])
    return ret
  def concat(self,other):
    ret = Ctnr();
    for i in range(0,self.length): ret.push(self[i])
    for i in range(0,other.length): ret.push(other[i])
    return ret
  def __str__(self):
    if (len(self.dict.keys())==self.length):
      ret = "["
      for k in range(0,self.length):
        v = self[k]
        if (isinstance(v,Ctnr)): ret += v.__str__()
        else: ret += str(v)
        ret+=","
      ret += "]"
      return ret;
    else:
      ret = "{"
      for k in self.dict.keys():
        ret += str(k)+":"
        v = self.dict[k]
        if (isinstance(v,Ctnr)): ret += v.__str__()
        else: ret += str(v)
        ret+=","
      ret += "}"
      return ret;
  def __repr__(self):
    return self.__str__()
  def __iter__(self):
    self.it = -1;
    return self
  def __next__(self):
    self.it += 1
    if (self.it >= self.length): raise StopIteration()
    return self[self.it]
globals()['Ctnr']=Ctnr;
class JSON:
  @staticmethod
  def stringify(x):
    return x;
#####
進制=1
退制=1
總算位=0
上位冪=1
下位冪=1
至大指=0
巨位冪=1
至巨數=1
至小指=0
微位冪=1
至微數=1
位極差=1
浮點零=0
浮點一=1
試界=lambda _:0
def 試界 (限):
	def _rand1(元):
		def _rand2(基):
			def _rand3(合):
				def _rand4(據):
					nonlocal 限;
					nonlocal 元;
					nonlocal 基;
					nonlocal 合;
					global 進制;
					global 退制;
					global 總算位;
					global 上位冪;
					global 下位冪;
					global 至大指;
					global 巨位冪;
					global 至巨數;
					global 至小指;
					global 微位冪;
					global 至微數;
					global 位極差;
					global 浮點零;
					global 浮點一;
					global 試界;
					造表列=lambda _:0
					def 造表列 (引):
						def _rand5(實):
							nonlocal 引;
							global 進制;
							global 退制;
							global 總算位;
							global 上位冪;
							global 下位冪;
							global 至大指;
							global 巨位冪;
							global 至巨數;
							global 至小指;
							global 微位冪;
							global 至微數;
							global 位極差;
							global 浮點零;
							global 浮點一;
							global 試界;
							nonlocal 造表列;
							表列={}
							表列={"引":引,"實":實,};
							return 表列
						return _rand5;

					新據=lambda _:0
					def 新據 (引):
						def _rand6(實):
							nonlocal 引;
							global 進制;
							global 退制;
							global 總算位;
							global 上位冪;
							global 下位冪;
							global 至大指;
							global 巨位冪;
							global 至巨數;
							global 至小指;
							global 微位冪;
							global 至微數;
							global 位極差;
							global 浮點零;
							global 浮點一;
							global 試界;
							nonlocal 造表列;
							nonlocal 新據;

							if 引>=限:
								return True

							_ans1=據(實);

							if _ans1:
								return True

							return False
						return _rand6;

					_ans2=新據(0)(元);

					if _ans2:
						_ans3=0;
						_ans4=元;
						_ans5=造表列(_ans3)(_ans4);
						return _ans5

					_ans6=新據(1)(基);

					if _ans6:
						_ans7=1;
						_ans8=基;
						_ans9=造表列(_ans7)(_ans8);
						return _ans9

					引=1
					實=基
					記表列=Ctnr()
					while (True):
						_ans10=引+引;

						新引=_ans10;
						_ans11=實;
						_ans12=實;
						_ans13=合(_ans11)(_ans12);

						新實=_ans13;
						_ans14=新據(新引)(新實);

						if _ans14:
							break

						_ans15=引;
						_ans16=實;
						_ans17=造表列(_ans15)(_ans16);
						記表列.push(_ans17)

						引=新引;

						實=新實;

					_ans18=記表列.length if type(記表列) != str else len(記表列);
					甲=_ans18;
					while (True):

						if 甲==0:
							break

						_ans19=記表列[甲-1];

						表列=_ans19;
						_ans20=表列["引"];
						_ans21=引+_ans20;

						新引=_ans21;
						_ans22=表列["實"];
						_ans23=實;
						_ans24=合(_ans22)(_ans23);

						新實=_ans24;
						_ans25=新據(新引)(新實);

						if _ans25:

							引=新引;

							實=新實;

						_ans26=甲-1;

						甲=_ans26;

					_ans27=引+1;
					_ans28=基;
					_ans29=實;
					_ans30=合(_ans28)(_ans29);
					_ans31=造表列(_ans27)(_ans30);
					return _ans31
				return _rand4;
			return _rand3;
		return _rand2;
	return _rand1;

盤古=lambda _:0
def 盤古():
	global 進制;
	global 退制;
	global 總算位;
	global 上位冪;
	global 下位冪;
	global 至大指;
	global 巨位冪;
	global 至巨數;
	global 至小指;
	global 微位冪;
	global 至微數;
	global 位極差;
	global 浮點零;
	global 浮點一;
	global 試界;
	global 盤古;
	_ans32=3/1;

	if _ans32==0:
		_ans33="告。計算機除不盡而捨餘者。不可行本算經之術。";
		print(_ans33);
		return 

	寅=0.5
	_ans34=寅-寅;

	卯=_ans34;
	_ans35=卯*卯;

	浮點零=_ans35;
	_ans36=浮點零+1;

	浮點一=_ans36;
	素數=Ctnr()
	素數.push(2,3,5,7,11,13)
	進制素因數=0

	進制=浮點一;
	for 法 in 素數:
		_ans37=法+1;
		_ans38=_ans37/法;
		_ans39=_ans38-1;
		_ans40=_ans39*法;

		餘=_ans40;

		if 餘==1:
			_ans41=進制*法;

			進制=_ans41;
			_ans42=進制素因數+1;

			進制素因數=_ans42;


		if 餘==0:
			_ans43="告。計算機除不盡而不得分釐者。不可行本算經之術。";
			print(_ans43);
			return 



	if 進制素因數>2:
		_ans44="告。計算機掩絲毫之瑕而求整者。不可行本算經之術。";
		print(_ans44);
		return 


	if 進制!=2:
		_ans45="告。計算機非二進者。不可行本算經之術。";
		print(_ans45);
		return 

	_ans46=1/進制;

	退制=_ans46;
	加=lambda _:0
	def 加 (甲):
		def _rand7(乙):
			nonlocal 甲;
			global 進制;
			global 退制;
			global 總算位;
			global 上位冪;
			global 下位冪;
			global 至大指;
			global 巨位冪;
			global 至巨數;
			global 至小指;
			global 微位冪;
			global 至微數;
			global 位極差;
			global 浮點零;
			global 浮點一;
			global 試界;
			global 盤古;
			nonlocal 寅;
			nonlocal 素數;
			nonlocal 進制素因數;
			nonlocal 加;
			_ans47=乙+甲;
			return _ans47
		return _rand7;

	乘=lambda _:0
	def 乘 (甲):
		def _rand8(乙):
			nonlocal 甲;
			global 進制;
			global 退制;
			global 總算位;
			global 上位冪;
			global 下位冪;
			global 至大指;
			global 巨位冪;
			global 至巨數;
			global 至小指;
			global 微位冪;
			global 至微數;
			global 位極差;
			global 浮點零;
			global 浮點一;
			global 試界;
			global 盤古;
			nonlocal 寅;
			nonlocal 素數;
			nonlocal 進制素因數;
			nonlocal 加;
			nonlocal 乘;
			_ans48=乙*甲;
			return _ans48
		return _rand8;

	位溢乎=lambda _:0
	def 位溢乎 (甲):
		global 進制;
		global 退制;
		global 總算位;
		global 上位冪;
		global 下位冪;
		global 至大指;
		global 巨位冪;
		global 至巨數;
		global 至小指;
		global 微位冪;
		global 至微數;
		global 位極差;
		global 浮點零;
		global 浮點一;
		global 試界;
		global 盤古;
		nonlocal 寅;
		nonlocal 素數;
		nonlocal 進制素因數;
		nonlocal 加;
		nonlocal 乘;
		nonlocal 位溢乎;
		_ans49=甲*進制;

		乙=_ans49;
		_ans50=乙+1;
		_ans51=_ans50-乙;

		if _ans51==1:
			return False

		else:
			return True


	試位限=10000
	_ans52=試界(試位限)(浮點一)(進制)(乘)(位溢乎);

	算限表=_ans52;
	_ans53=算限表["引"];

	if _ans53>=試位限:
		_ans54="告。計算機算位無限者。不可行本算經之術。";
		print(_ans54);
		return 

	_ans55=算限表["引"];
	_ans56=_ans55+1;

	總算位=_ans56;
	_ans57=算限表["實"];

	上位冪=_ans57;
	_ans58=1/上位冪;

	下位冪=_ans58;
	_ans59=1+下位冪;
	_ans60=_ans59-1;

	if _ans60!=下位冪:
		_ans61="告。計算機非二進者。不可行本算經之術。";
		print(_ans61);
		return 

	上溢乎=lambda _:0
	def 上溢乎 (甲):
		global 進制;
		global 退制;
		global 總算位;
		global 上位冪;
		global 下位冪;
		global 至大指;
		global 巨位冪;
		global 至巨數;
		global 至小指;
		global 微位冪;
		global 至微數;
		global 位極差;
		global 浮點零;
		global 浮點一;
		global 試界;
		global 盤古;
		nonlocal 寅;
		nonlocal 素數;
		nonlocal 進制素因數;
		nonlocal 加;
		nonlocal 乘;
		nonlocal 位溢乎;
		nonlocal 試位限;
		nonlocal 上溢乎;
		_ans62=甲*進制;

		乙=_ans62;
		_ans63=乙*進制;

		if _ans63>乙:
			return False

		else:
			return True


	下溢乎=lambda _:0
	def 下溢乎 (甲):
		global 進制;
		global 退制;
		global 總算位;
		global 上位冪;
		global 下位冪;
		global 至大指;
		global 巨位冪;
		global 至巨數;
		global 至小指;
		global 微位冪;
		global 至微數;
		global 位極差;
		global 浮點零;
		global 浮點一;
		global 試界;
		global 盤古;
		nonlocal 寅;
		nonlocal 素數;
		nonlocal 進制素因數;
		nonlocal 加;
		nonlocal 乘;
		nonlocal 位溢乎;
		nonlocal 試位限;
		nonlocal 上溢乎;
		nonlocal 下溢乎;
		_ans64=甲*退制;

		乙=_ans64;

		if 乙==0:
			return True


		if 乙<甲:
			return False

		return True

	試指限=100000000
	_ans65=試界(試指限)(浮點一)(進制)(乘)(上溢乎);

	上限表=_ans65;
	_ans66=上限表["引"];

	至大指=_ans66;
	_ans67=上限表["實"];

	巨位冪=_ans67;
	_ans68=進制-下位冪;
	_ans69=_ans68*巨位冪;

	至巨數=_ans69;
	_ans70=試界(試指限)(浮點一)(退制)(乘)(下溢乎);

	下限表=_ans70;
	_ans71=下限表["引"];
	_ans72=總算位-_ans71;
	_ans73=_ans72-1;

	至小指=_ans73;
	_ans74=下限表["實"];

	至微數=_ans74;
	_ans75=至微數*上位冪;

	微位冪=_ans75;
	_ans76=至小指-總算位;
	_ans77=至大指-_ans76;

	位極差=_ans77;
	""" "以上驗算制。" """

_ans78=盤古();
""" "圓周率。同Javascript之Math.PI也。" """
圓周率=3.141592653589793238462643383279502884197
""" "倍圓周率。同Javascript之Math.PI * 2也。" """
倍圓周率=6.283185307179586476925286766559005768394
""" "半圓周率。同Javascript之Math.PI / 2也。" """
半圓周率=1.570796326794896619231321691639751442099
""" "四分圓周率。同Javascript之Math.PI / 4也。" """
四分圓周率=0.7853981633974483096156608458198757210493
""" "自然常數。同Javascript之Math.E也。" """
自然常數=2.718281828459045235360287471352662497757
""" "歐拉常數。同Javascript之0.5772156649015329也。" """
歐拉常數=0.5772156649015328606065120900824024310422
""" "黃金分割數。同Javascript之1.618033988749895也。" """
黃金分割數=1.61803398874989484820458683436563811772
""" "二之平方根。同Javascript之Math.SQRT2也。" """
二之平方根=1.41421356237309504880168872420969807857
""" "二之對數。同Javascript之Math.LN2也。" """
二之對數=0.6931471805599453094172321214581765680755
""" "十之對數。同Javascript之Math.LN10也。" """
十之對數=2.302585092994045684017991454684364207601
""" "不可算數乎。同Javascript之Number.isNaN也。" """
不可算數乎=lambda _:0
def 不可算數乎 (甲):
	global 進制;
	global 退制;
	global 總算位;
	global 上位冪;
	global 下位冪;
	global 至大指;
	global 巨位冪;
	global 至巨數;
	global 至小指;
	global 微位冪;
	global 至微數;
	global 位極差;
	global 浮點零;
	global 浮點一;
	global 試界;
	global 盤古;
	global 圓周率;
	global 倍圓周率;
	global 半圓周率;
	global 四分圓周率;
	global 自然常數;
	global 歐拉常數;
	global 黃金分割數;
	global 二之平方根;
	global 二之對數;
	global 十之對數;
	global 不可算數乎;

	if 甲==甲:
		return False

	else:
		return True


下溢=lambda _:0
def 下溢 (符):
	global 進制;
	global 退制;
	global 總算位;
	global 上位冪;
	global 下位冪;
	global 至大指;
	global 巨位冪;
	global 至巨數;
	global 至小指;
	global 微位冪;
	global 至微數;
	global 位極差;
	global 浮點零;
	global 浮點一;
	global 試界;
	global 盤古;
	global 圓周率;
	global 倍圓周率;
	global 半圓周率;
	global 四分圓周率;
	global 自然常數;
	global 歐拉常數;
	global 黃金分割數;
	global 二之平方根;
	global 二之對數;
	global 十之對數;
	global 不可算數乎;
	global 下溢;
	_ans79=符*微位冪;
	_ans80=_ans79*至微數;
	return _ans80

上溢=lambda _:0
def 上溢 (符):
	global 進制;
	global 退制;
	global 總算位;
	global 上位冪;
	global 下位冪;
	global 至大指;
	global 巨位冪;
	global 至巨數;
	global 至小指;
	global 微位冪;
	global 至微數;
	global 位極差;
	global 浮點零;
	global 浮點一;
	global 試界;
	global 盤古;
	global 圓周率;
	global 倍圓周率;
	global 半圓周率;
	global 四分圓周率;
	global 自然常數;
	global 歐拉常數;
	global 黃金分割數;
	global 二之平方根;
	global 二之對數;
	global 十之對數;
	global 不可算數乎;
	global 下溢;
	global 上溢;
	_ans81=符*至巨數;
	_ans82=_ans81*至巨數;
	return _ans82

除以零=lambda _:0
def 除以零 (符):
	global 進制;
	global 退制;
	global 總算位;
	global 上位冪;
	global 下位冪;
	global 至大指;
	global 巨位冪;
	global 至巨數;
	global 至小指;
	global 微位冪;
	global 至微數;
	global 位極差;
	global 浮點零;
	global 浮點一;
	global 試界;
	global 盤古;
	global 圓周率;
	global 倍圓周率;
	global 半圓周率;
	global 四分圓周率;
	global 自然常數;
	global 歐拉常數;
	global 黃金分割數;
	global 二之平方根;
	global 二之對數;
	global 十之對數;
	global 不可算數乎;
	global 下溢;
	global 上溢;
	global 除以零;
	_ans83=符/浮點零;
	return _ans83

不可算=lambda _:0
def 不可算():
	global 進制;
	global 退制;
	global 總算位;
	global 上位冪;
	global 下位冪;
	global 至大指;
	global 巨位冪;
	global 至巨數;
	global 至小指;
	global 微位冪;
	global 至微數;
	global 位極差;
	global 浮點零;
	global 浮點一;
	global 試界;
	global 盤古;
	global 圓周率;
	global 倍圓周率;
	global 半圓周率;
	global 四分圓周率;
	global 自然常數;
	global 歐拉常數;
	global 黃金分割數;
	global 二之平方根;
	global 二之對數;
	global 十之對數;
	global 不可算數乎;
	global 下溢;
	global 上溢;
	global 除以零;
	global 不可算;
	_ans84=浮點零/浮點零;
	return _ans84

求進冪=lambda _:0
def 求進冪 (位):
	global 進制;
	global 退制;
	global 總算位;
	global 上位冪;
	global 下位冪;
	global 至大指;
	global 巨位冪;
	global 至巨數;
	global 至小指;
	global 微位冪;
	global 至微數;
	global 位極差;
	global 浮點零;
	global 浮點一;
	global 試界;
	global 盤古;
	global 圓周率;
	global 倍圓周率;
	global 半圓周率;
	global 四分圓周率;
	global 自然常數;
	global 歐拉常數;
	global 黃金分割數;
	global 二之平方根;
	global 二之對數;
	global 十之對數;
	global 不可算數乎;
	global 下溢;
	global 上溢;
	global 除以零;
	global 不可算;
	global 求進冪;
	吾之冪=lambda _:0
	def 吾之冪 (底):
		def _rand9(指):
			nonlocal 底;
			global 進制;
			global 退制;
			global 總算位;
			global 上位冪;
			global 下位冪;
			global 至大指;
			global 巨位冪;
			global 至巨數;
			global 至小指;
			global 微位冪;
			global 至微數;
			global 位極差;
			global 浮點零;
			global 浮點一;
			global 試界;
			global 盤古;
			global 圓周率;
			global 倍圓周率;
			global 半圓周率;
			global 四分圓周率;
			global 自然常數;
			global 歐拉常數;
			global 黃金分割數;
			global 二之平方根;
			global 二之對數;
			global 十之對數;
			global 不可算數乎;
			global 下溢;
			global 上溢;
			global 除以零;
			global 不可算;
			global 求進冪;
			nonlocal 吾之冪;
			甲=底
			冪=浮點一
			while (True):

				if 指==0:
					break

				_ans85=指%2;

				餘=_ans85;

				if 餘>0:
					_ans86=冪*甲;

					冪=_ans86;

				_ans87=甲*甲;

				甲=_ans87;
				_ans88=指-餘;
				_ans89=_ans88/2;

				指=_ans89;

			return 冪
		return _rand9;


	if 位<0:
		_ans90=退制;
		_ans91=0-位;
		_ans92=吾之冪(_ans90)(_ans91);
		return _ans92

	else:
		_ans93=進制;
		_ans94=位;
		_ans95=吾之冪(_ans93)(_ans94);
		return _ans95


取位常數甲=0
取位常數乙=0
取位上溢限=0
分算常數=0
分算上溢限甲=0
分算上溢限乙=0
伏羲=lambda _:0
def 伏羲():
	global 進制;
	global 退制;
	global 總算位;
	global 上位冪;
	global 下位冪;
	global 至大指;
	global 巨位冪;
	global 至巨數;
	global 至小指;
	global 微位冪;
	global 至微數;
	global 位極差;
	global 浮點零;
	global 浮點一;
	global 試界;
	global 盤古;
	global 圓周率;
	global 倍圓周率;
	global 半圓周率;
	global 四分圓周率;
	global 自然常數;
	global 歐拉常數;
	global 黃金分割數;
	global 二之平方根;
	global 二之對數;
	global 十之對數;
	global 不可算數乎;
	global 下溢;
	global 上溢;
	global 除以零;
	global 不可算;
	global 求進冪;
	global 取位常數甲;
	global 取位常數乙;
	global 取位上溢限;
	global 分算常數;
	global 分算上溢限甲;
	global 分算上溢限乙;
	global 伏羲;
	_ans96=上位冪+1;

	取位常數甲=_ans96;
	_ans97=下位冪/2;
	_ans98=1-_ans97;

	取位常數乙=_ans98;
	_ans99=巨位冪/上位冪;

	取位上溢限=_ans99;
	_ans100=總算位+1;

	甲=_ans100;
	_ans101=甲%2;
	_ans102=甲-_ans101;
	_ans103=_ans102/2;

	半算位=_ans103;
	_ans104=求進冪(半算位);

	半位冪=_ans104;
	_ans105=半位冪+1;

	分算常數=_ans105;
	_ans106=巨位冪/半位冪;

	分算上溢限甲=_ans106;
	_ans107=下位冪*半位冪;
	_ans108=進制-_ans107;
	_ans109=_ans108*巨位冪;

	分算上溢限乙=_ans109;

_ans110=伏羲();
取本位冪=lambda _:0
def 取本位冪 (甲):
	global 進制;
	global 退制;
	global 總算位;
	global 上位冪;
	global 下位冪;
	global 至大指;
	global 巨位冪;
	global 至巨數;
	global 至小指;
	global 微位冪;
	global 至微數;
	global 位極差;
	global 浮點零;
	global 浮點一;
	global 試界;
	global 盤古;
	global 圓周率;
	global 倍圓周率;
	global 半圓周率;
	global 四分圓周率;
	global 自然常數;
	global 歐拉常數;
	global 黃金分割數;
	global 二之平方根;
	global 二之對數;
	global 十之對數;
	global 不可算數乎;
	global 下溢;
	global 上溢;
	global 除以零;
	global 不可算;
	global 求進冪;
	global 取位常數甲;
	global 取位常數乙;
	global 取位上溢限;
	global 分算常數;
	global 分算上溢限甲;
	global 分算上溢限乙;
	global 伏羲;
	global 取本位冪;
	""" "二進者方可施是術。" """
	_ans111=絕對(甲);

	乙=_ans111;

	if 乙<取位上溢限:
		_ans112=乙*取位常數甲;

		丙=_ans112;
		_ans113=丙*取位常數乙;

		丁=_ans113;
		_ans114=丙-丁;
		return _ans114

	else:
		_ans115=乙*下位冪;
		_ans116=_ans115*下位冪;

		丙=_ans116;

		if 丙<取位上溢限:
			_ans117=取本位冪(丙);
			_ans118=_ans117*上位冪;
			_ans119=_ans118*上位冪;
			return _ans119

		else:
			return 乙



取內鄰數=lambda _:0
def 取內鄰數 (甲):
	global 進制;
	global 退制;
	global 總算位;
	global 上位冪;
	global 下位冪;
	global 至大指;
	global 巨位冪;
	global 至巨數;
	global 至小指;
	global 微位冪;
	global 至微數;
	global 位極差;
	global 浮點零;
	global 浮點一;
	global 試界;
	global 盤古;
	global 圓周率;
	global 倍圓周率;
	global 半圓周率;
	global 四分圓周率;
	global 自然常數;
	global 歐拉常數;
	global 黃金分割數;
	global 二之平方根;
	global 二之對數;
	global 十之對數;
	global 不可算數乎;
	global 下溢;
	global 上溢;
	global 除以零;
	global 不可算;
	global 求進冪;
	global 取位常數甲;
	global 取位常數乙;
	global 取位上溢限;
	global 分算常數;
	global 分算上溢限甲;
	global 分算上溢限乙;
	global 伏羲;
	global 取本位冪;
	global 取內鄰數;
	""" "二進者方可施是術。" """
	_ans120=甲*取位常數乙;

	乙=_ans120;

	if 乙!=甲:
		return 乙


	if 甲==0:
		return 甲

	_ans121=正負(甲);

	符=_ans121;
	_ans122=甲*符;

	丙=_ans122;

	if 丙>至巨數:
		_ans123=至巨數*符;
		return _ans123

	_ans124=丙-至微數;
	_ans125=_ans124*符;
	return _ans125

取外鄰數=lambda _:0
def 取外鄰數 (甲):
	global 進制;
	global 退制;
	global 總算位;
	global 上位冪;
	global 下位冪;
	global 至大指;
	global 巨位冪;
	global 至巨數;
	global 至小指;
	global 微位冪;
	global 至微數;
	global 位極差;
	global 浮點零;
	global 浮點一;
	global 試界;
	global 盤古;
	global 圓周率;
	global 倍圓周率;
	global 半圓周率;
	global 四分圓周率;
	global 自然常數;
	global 歐拉常數;
	global 黃金分割數;
	global 二之平方根;
	global 二之對數;
	global 十之對數;
	global 不可算數乎;
	global 下溢;
	global 上溢;
	global 除以零;
	global 不可算;
	global 求進冪;
	global 取位常數甲;
	global 取位常數乙;
	global 取位上溢限;
	global 分算常數;
	global 分算上溢限甲;
	global 分算上溢限乙;
	global 伏羲;
	global 取本位冪;
	global 取內鄰數;
	global 取外鄰數;
	""" "二進者方可施是術。" """
	_ans126=正負(甲);

	符=_ans126;
	_ans127=取本位冪(甲);
	_ans128=_ans127*下位冪;
	_ans129=_ans128*符;
	_ans130=_ans129+甲;

	乙=_ans130;

	if 乙!=甲:
		return 乙


	if 甲==0:
		return 至微數

	_ans131=甲*符;
	_ans132=_ans131+至微數;
	_ans133=_ans132*符;
	return _ans133

分算=lambda _:0
def 分算 (甲):
	global 進制;
	global 退制;
	global 總算位;
	global 上位冪;
	global 下位冪;
	global 至大指;
	global 巨位冪;
	global 至巨數;
	global 至小指;
	global 微位冪;
	global 至微數;
	global 位極差;
	global 浮點零;
	global 浮點一;
	global 試界;
	global 盤古;
	global 圓周率;
	global 倍圓周率;
	global 半圓周率;
	global 四分圓周率;
	global 自然常數;
	global 歐拉常數;
	global 黃金分割數;
	global 二之平方根;
	global 二之對數;
	global 十之對數;
	global 不可算數乎;
	global 下溢;
	global 上溢;
	global 除以零;
	global 不可算;
	global 求進冪;
	global 取位常數甲;
	global 取位常數乙;
	global 取位上溢限;
	global 分算常數;
	global 分算上溢限甲;
	global 分算上溢限乙;
	global 伏羲;
	global 取本位冪;
	global 取內鄰數;
	global 取外鄰數;
	global 分算;
	""" "分算者。其位上下二分。借二算布之也。" """
	二算=Ctnr()
	_ans134=絕對(甲);

	乙=_ans134;

	if 乙<分算上溢限甲:
		_ans135=甲*分算常數;

		丙=_ans135;
		_ans136=甲-丙;

		丁=_ans136;
		_ans137=丙+丁;

		上甲=_ans137;
		二算.push(上甲)
		_ans138=甲-上甲;
		二算.push(_ans138)

	else:

		if 乙<分算上溢限乙:
			_ans139=甲*下位冪;

			丙=_ans139;
			_ans140=分算(丙);

			丁=_ans140;
			for 戊 in 丁:
				_ans141=戊*上位冪;
				二算.push(_ans141)


		else:
			_ans142=乙-分算上溢限乙;

			丙=_ans142;

			if 丙<分算上溢限乙:
				_ans143=正負(甲);

				符=_ans143;
				_ans144=分算上溢限乙*符;
				二算.push(_ans144)
				_ans145=丙*符;
				二算.push(_ans145)

			else:
				二算.push(甲,甲)



	return 二算

造雙數=lambda _:0
def 造雙數 (上):
	def _rand10(下):
		nonlocal 上;
		global 進制;
		global 退制;
		global 總算位;
		global 上位冪;
		global 下位冪;
		global 至大指;
		global 巨位冪;
		global 至巨數;
		global 至小指;
		global 微位冪;
		global 至微數;
		global 位極差;
		global 浮點零;
		global 浮點一;
		global 試界;
		global 盤古;
		global 圓周率;
		global 倍圓周率;
		global 半圓周率;
		global 四分圓周率;
		global 自然常數;
		global 歐拉常數;
		global 黃金分割數;
		global 二之平方根;
		global 二之對數;
		global 十之對數;
		global 不可算數乎;
		global 下溢;
		global 上溢;
		global 除以零;
		global 不可算;
		global 求進冪;
		global 取位常數甲;
		global 取位常數乙;
		global 取位上溢限;
		global 分算常數;
		global 分算上溢限甲;
		global 分算上溢限乙;
		global 伏羲;
		global 取本位冪;
		global 取內鄰數;
		global 取外鄰數;
		global 分算;
		global 造雙數;
		""" "雙數者。以二算布一數。其位倍之。" """
		雙=Ctnr()
		雙.push(上,下)
		return 雙
	return _rand10;

雙數取反=lambda _:0
def 雙數取反 (甲):
	global 進制;
	global 退制;
	global 總算位;
	global 上位冪;
	global 下位冪;
	global 至大指;
	global 巨位冪;
	global 至巨數;
	global 至小指;
	global 微位冪;
	global 至微數;
	global 位極差;
	global 浮點零;
	global 浮點一;
	global 試界;
	global 盤古;
	global 圓周率;
	global 倍圓周率;
	global 半圓周率;
	global 四分圓周率;
	global 自然常數;
	global 歐拉常數;
	global 黃金分割數;
	global 二之平方根;
	global 二之對數;
	global 十之對數;
	global 不可算數乎;
	global 下溢;
	global 上溢;
	global 除以零;
	global 不可算;
	global 求進冪;
	global 取位常數甲;
	global 取位常數乙;
	global 取位上溢限;
	global 分算常數;
	global 分算上溢限甲;
	global 分算上溢限乙;
	global 伏羲;
	global 取本位冪;
	global 取內鄰數;
	global 取外鄰數;
	global 分算;
	global 造雙數;
	global 雙數取反;
	_ans146=甲[1-1];
	_ans147=_ans146*-1;

	上=_ans147;
	_ans148=甲[2-1];
	_ans149=_ans148*-1;

	下=_ans149;
	_ans150=造雙數(上)(下);
	return _ans150

以小加大得雙=lambda _:0
def 以小加大得雙 (小):
	def _rand11(大):
		nonlocal 小;
		global 進制;
		global 退制;
		global 總算位;
		global 上位冪;
		global 下位冪;
		global 至大指;
		global 巨位冪;
		global 至巨數;
		global 至小指;
		global 微位冪;
		global 至微數;
		global 位極差;
		global 浮點零;
		global 浮點一;
		global 試界;
		global 盤古;
		global 圓周率;
		global 倍圓周率;
		global 半圓周率;
		global 四分圓周率;
		global 自然常數;
		global 歐拉常數;
		global 黃金分割數;
		global 二之平方根;
		global 二之對數;
		global 十之對數;
		global 不可算數乎;
		global 下溢;
		global 上溢;
		global 除以零;
		global 不可算;
		global 求進冪;
		global 取位常數甲;
		global 取位常數乙;
		global 取位上溢限;
		global 分算常數;
		global 分算上溢限甲;
		global 分算上溢限乙;
		global 伏羲;
		global 取本位冪;
		global 取內鄰數;
		global 取外鄰數;
		global 分算;
		global 造雙數;
		global 雙數取反;
		global 以小加大得雙;
		""" "大小者。二數移位之大小也。或前小而後大。或同。不可反之。" """
		_ans151=大+小;

		上和=_ans151;
		_ans152=上和-大;

		丙=_ans152;
		_ans153=小-丙;

		下和=_ans153;
		_ans154=造雙數(上和)(下和);
		return _ans154
	return _rand11;

相加得雙=lambda _:0
def 相加得雙 (甲):
	def _rand12(乙):
		nonlocal 甲;
		global 進制;
		global 退制;
		global 總算位;
		global 上位冪;
		global 下位冪;
		global 至大指;
		global 巨位冪;
		global 至巨數;
		global 至小指;
		global 微位冪;
		global 至微數;
		global 位極差;
		global 浮點零;
		global 浮點一;
		global 試界;
		global 盤古;
		global 圓周率;
		global 倍圓周率;
		global 半圓周率;
		global 四分圓周率;
		global 自然常數;
		global 歐拉常數;
		global 黃金分割數;
		global 二之平方根;
		global 二之對數;
		global 十之對數;
		global 不可算數乎;
		global 下溢;
		global 上溢;
		global 除以零;
		global 不可算;
		global 求進冪;
		global 取位常數甲;
		global 取位常數乙;
		global 取位上溢限;
		global 分算常數;
		global 分算上溢限甲;
		global 分算上溢限乙;
		global 伏羲;
		global 取本位冪;
		global 取內鄰數;
		global 取外鄰數;
		global 分算;
		global 造雙數;
		global 雙數取反;
		global 以小加大得雙;
		global 相加得雙;
		_ans155=乙+甲;

		上和=_ans155;
		_ans156=上和-乙;

		丙=_ans156;
		_ans157=上和-丙;

		丁=_ans157;
		_ans158=甲-丙;

		戊=_ans158;
		_ans159=乙-丁;

		己=_ans159;
		_ans160=己+戊;

		下和=_ans160;
		_ans161=造雙數(上和)(下和);
		return _ans161
	return _rand12;

加單於雙=lambda _:0
def 加單於雙 (甲):
	def _rand13(乙):
		nonlocal 甲;
		global 進制;
		global 退制;
		global 總算位;
		global 上位冪;
		global 下位冪;
		global 至大指;
		global 巨位冪;
		global 至巨數;
		global 至小指;
		global 微位冪;
		global 至微數;
		global 位極差;
		global 浮點零;
		global 浮點一;
		global 試界;
		global 盤古;
		global 圓周率;
		global 倍圓周率;
		global 半圓周率;
		global 四分圓周率;
		global 自然常數;
		global 歐拉常數;
		global 黃金分割數;
		global 二之平方根;
		global 二之對數;
		global 十之對數;
		global 不可算數乎;
		global 下溢;
		global 上溢;
		global 除以零;
		global 不可算;
		global 求進冪;
		global 取位常數甲;
		global 取位常數乙;
		global 取位上溢限;
		global 分算常數;
		global 分算上溢限甲;
		global 分算上溢限乙;
		global 伏羲;
		global 取本位冪;
		global 取內鄰數;
		global 取外鄰數;
		global 分算;
		global 造雙數;
		global 雙數取反;
		global 以小加大得雙;
		global 相加得雙;
		global 加單於雙;
		_ans162=乙[1-1];

		上乙=_ans162;
		_ans163=乙[2-1];

		下乙=_ans163;
		_ans164=相加得雙(甲)(上乙);

		丙=_ans164;
		_ans165=丙[2-1];
		_ans166=下乙+_ans165;
		_ans167=丙[1-1];
		_ans168=以小加大得雙(_ans166)(_ans167);
		return _ans168
	return _rand13;

以單減雙得單=lambda _:0
def 以單減雙得單 (甲):
	def _rand14(乙):
		nonlocal 甲;
		global 進制;
		global 退制;
		global 總算位;
		global 上位冪;
		global 下位冪;
		global 至大指;
		global 巨位冪;
		global 至巨數;
		global 至小指;
		global 微位冪;
		global 至微數;
		global 位極差;
		global 浮點零;
		global 浮點一;
		global 試界;
		global 盤古;
		global 圓周率;
		global 倍圓周率;
		global 半圓周率;
		global 四分圓周率;
		global 自然常數;
		global 歐拉常數;
		global 黃金分割數;
		global 二之平方根;
		global 二之對數;
		global 十之對數;
		global 不可算數乎;
		global 下溢;
		global 上溢;
		global 除以零;
		global 不可算;
		global 求進冪;
		global 取位常數甲;
		global 取位常數乙;
		global 取位上溢限;
		global 分算常數;
		global 分算上溢限甲;
		global 分算上溢限乙;
		global 伏羲;
		global 取本位冪;
		global 取內鄰數;
		global 取外鄰數;
		global 分算;
		global 造雙數;
		global 雙數取反;
		global 以小加大得雙;
		global 相加得雙;
		global 加單於雙;
		global 以單減雙得單;
		_ans169=乙[1-1];

		上乙=_ans169;
		_ans170=乙[2-1];

		下乙=_ans170;
		_ans171=上乙-甲;
		_ans172=_ans171+下乙;
		return _ans172
	return _rand14;

加雙於雙=lambda _:0
def 加雙於雙 (甲):
	def _rand15(乙):
		nonlocal 甲;
		global 進制;
		global 退制;
		global 總算位;
		global 上位冪;
		global 下位冪;
		global 至大指;
		global 巨位冪;
		global 至巨數;
		global 至小指;
		global 微位冪;
		global 至微數;
		global 位極差;
		global 浮點零;
		global 浮點一;
		global 試界;
		global 盤古;
		global 圓周率;
		global 倍圓周率;
		global 半圓周率;
		global 四分圓周率;
		global 自然常數;
		global 歐拉常數;
		global 黃金分割數;
		global 二之平方根;
		global 二之對數;
		global 十之對數;
		global 不可算數乎;
		global 下溢;
		global 上溢;
		global 除以零;
		global 不可算;
		global 求進冪;
		global 取位常數甲;
		global 取位常數乙;
		global 取位上溢限;
		global 分算常數;
		global 分算上溢限甲;
		global 分算上溢限乙;
		global 伏羲;
		global 取本位冪;
		global 取內鄰數;
		global 取外鄰數;
		global 分算;
		global 造雙數;
		global 雙數取反;
		global 以小加大得雙;
		global 相加得雙;
		global 加單於雙;
		global 以單減雙得單;
		global 加雙於雙;
		_ans173=甲[1-1];
		_ans174=乙[1-1];
		_ans175=相加得雙(_ans173)(_ans174);

		丙=_ans175;
		_ans176=甲[2-1];
		_ans177=乙[2-1];
		_ans178=相加得雙(_ans176)(_ans177);

		丁=_ans178;
		_ans179=丙[1-1];

		上丙=_ans179;
		_ans180=丙[2-1];

		下丙=_ans180;
		_ans181=丁[1-1];
		_ans182=下丙+_ans181;
		_ans183=上丙;
		_ans184=以小加大得雙(_ans182)(_ans183);

		戊=_ans184;
		_ans185=戊[1-1];

		上戊=_ans185;
		_ans186=戊[2-1];

		下戊=_ans186;
		_ans187=丁[2-1];
		_ans188=下戊+_ans187;
		_ans189=上戊;
		_ans190=以小加大得雙(_ans188)(_ans189);
		return _ans190
	return _rand15;

自乘得雙=lambda _:0
def 自乘得雙 (甲):
	global 進制;
	global 退制;
	global 總算位;
	global 上位冪;
	global 下位冪;
	global 至大指;
	global 巨位冪;
	global 至巨數;
	global 至小指;
	global 微位冪;
	global 至微數;
	global 位極差;
	global 浮點零;
	global 浮點一;
	global 試界;
	global 盤古;
	global 圓周率;
	global 倍圓周率;
	global 半圓周率;
	global 四分圓周率;
	global 自然常數;
	global 歐拉常數;
	global 黃金分割數;
	global 二之平方根;
	global 二之對數;
	global 十之對數;
	global 不可算數乎;
	global 下溢;
	global 上溢;
	global 除以零;
	global 不可算;
	global 求進冪;
	global 取位常數甲;
	global 取位常數乙;
	global 取位上溢限;
	global 分算常數;
	global 分算上溢限甲;
	global 分算上溢限乙;
	global 伏羲;
	global 取本位冪;
	global 取內鄰數;
	global 取外鄰數;
	global 分算;
	global 造雙數;
	global 雙數取反;
	global 以小加大得雙;
	global 相加得雙;
	global 加單於雙;
	global 以單減雙得單;
	global 加雙於雙;
	global 自乘得雙;
	_ans191=甲*甲;

	上方=_ans191;
	_ans192=分算(甲);

	分甲=_ans192;
	_ans193=分甲[1-1];

	上甲=_ans193;
	_ans194=分甲[2-1];

	下甲=_ans194;
	_ans195=上甲*上甲;
	_ans196=_ans195-上方;

	丙=_ans196;
	_ans197=下甲*上甲;
	_ans198=_ans197*2;
	_ans199=丙+_ans198;

	丁=_ans199;
	_ans200=下甲*下甲;
	_ans201=丁+_ans200;

	下方=_ans201;
	_ans202=造雙數(上方)(下方);
	return _ans202

相乘得雙=lambda _:0
def 相乘得雙 (甲):
	def _rand16(乙):
		nonlocal 甲;
		global 進制;
		global 退制;
		global 總算位;
		global 上位冪;
		global 下位冪;
		global 至大指;
		global 巨位冪;
		global 至巨數;
		global 至小指;
		global 微位冪;
		global 至微數;
		global 位極差;
		global 浮點零;
		global 浮點一;
		global 試界;
		global 盤古;
		global 圓周率;
		global 倍圓周率;
		global 半圓周率;
		global 四分圓周率;
		global 自然常數;
		global 歐拉常數;
		global 黃金分割數;
		global 二之平方根;
		global 二之對數;
		global 十之對數;
		global 不可算數乎;
		global 下溢;
		global 上溢;
		global 除以零;
		global 不可算;
		global 求進冪;
		global 取位常數甲;
		global 取位常數乙;
		global 取位上溢限;
		global 分算常數;
		global 分算上溢限甲;
		global 分算上溢限乙;
		global 伏羲;
		global 取本位冪;
		global 取內鄰數;
		global 取外鄰數;
		global 分算;
		global 造雙數;
		global 雙數取反;
		global 以小加大得雙;
		global 相加得雙;
		global 加單於雙;
		global 以單減雙得單;
		global 加雙於雙;
		global 自乘得雙;
		global 相乘得雙;
		_ans203=甲*乙;

		上積=_ans203;
		_ans204=分算(甲);

		分甲=_ans204;
		_ans205=分甲[1-1];

		上甲=_ans205;
		_ans206=分甲[2-1];

		下甲=_ans206;
		_ans207=分算(乙);

		分乙=_ans207;
		_ans208=分乙[1-1];

		上乙=_ans208;
		_ans209=分乙[2-1];

		下乙=_ans209;
		_ans210=上乙*上甲;
		_ans211=_ans210-上積;

		丙=_ans211;
		_ans212=下乙*上甲;
		_ans213=丙+_ans212;

		丁=_ans213;
		_ans214=上乙*下甲;
		_ans215=丁+_ans214;

		戊=_ans215;
		_ans216=下乙*下甲;
		_ans217=戊+_ans216;

		下積=_ans217;
		_ans218=造雙數(上積)(下積);
		return _ans218
	return _rand16;

乘單於雙=lambda _:0
def 乘單於雙 (甲):
	def _rand17(乙):
		nonlocal 甲;
		global 進制;
		global 退制;
		global 總算位;
		global 上位冪;
		global 下位冪;
		global 至大指;
		global 巨位冪;
		global 至巨數;
		global 至小指;
		global 微位冪;
		global 至微數;
		global 位極差;
		global 浮點零;
		global 浮點一;
		global 試界;
		global 盤古;
		global 圓周率;
		global 倍圓周率;
		global 半圓周率;
		global 四分圓周率;
		global 自然常數;
		global 歐拉常數;
		global 黃金分割數;
		global 二之平方根;
		global 二之對數;
		global 十之對數;
		global 不可算數乎;
		global 下溢;
		global 上溢;
		global 除以零;
		global 不可算;
		global 求進冪;
		global 取位常數甲;
		global 取位常數乙;
		global 取位上溢限;
		global 分算常數;
		global 分算上溢限甲;
		global 分算上溢限乙;
		global 伏羲;
		global 取本位冪;
		global 取內鄰數;
		global 取外鄰數;
		global 分算;
		global 造雙數;
		global 雙數取反;
		global 以小加大得雙;
		global 相加得雙;
		global 加單於雙;
		global 以單減雙得單;
		global 加雙於雙;
		global 自乘得雙;
		global 相乘得雙;
		global 乘單於雙;
		_ans219=乙[1-1];

		上乙=_ans219;
		_ans220=乙[2-1];

		下乙=_ans220;
		_ans221=相乘得雙(甲)(上乙);

		丙=_ans221;
		_ans222=下乙*甲;

		丁=_ans222;
		_ans223=丙[2-1];
		_ans224=_ans223+丁;
		_ans225=丙[1-1];
		_ans226=以小加大得雙(_ans224)(_ans225);
		return _ans226
	return _rand17;

雙數自乘=lambda _:0
def 雙數自乘 (甲):
	global 進制;
	global 退制;
	global 總算位;
	global 上位冪;
	global 下位冪;
	global 至大指;
	global 巨位冪;
	global 至巨數;
	global 至小指;
	global 微位冪;
	global 至微數;
	global 位極差;
	global 浮點零;
	global 浮點一;
	global 試界;
	global 盤古;
	global 圓周率;
	global 倍圓周率;
	global 半圓周率;
	global 四分圓周率;
	global 自然常數;
	global 歐拉常數;
	global 黃金分割數;
	global 二之平方根;
	global 二之對數;
	global 十之對數;
	global 不可算數乎;
	global 下溢;
	global 上溢;
	global 除以零;
	global 不可算;
	global 求進冪;
	global 取位常數甲;
	global 取位常數乙;
	global 取位上溢限;
	global 分算常數;
	global 分算上溢限甲;
	global 分算上溢限乙;
	global 伏羲;
	global 取本位冪;
	global 取內鄰數;
	global 取外鄰數;
	global 分算;
	global 造雙數;
	global 雙數取反;
	global 以小加大得雙;
	global 相加得雙;
	global 加單於雙;
	global 以單減雙得單;
	global 加雙於雙;
	global 自乘得雙;
	global 相乘得雙;
	global 乘單於雙;
	global 雙數自乘;
	_ans227=甲[1-1];

	上甲=_ans227;
	_ans228=甲[2-1];

	下甲=_ans228;
	_ans229=自乘得雙(上甲);

	乙=_ans229;
	_ans230=下甲*上甲;
	_ans231=_ans230*2;

	丙=_ans231;
	_ans232=乙[2-1];
	_ans233=_ans232+丙;
	_ans234=乙[1-1];
	_ans235=以小加大得雙(_ans233)(_ans234);
	return _ans235

乘雙於雙=lambda _:0
def 乘雙於雙 (甲):
	def _rand18(乙):
		nonlocal 甲;
		global 進制;
		global 退制;
		global 總算位;
		global 上位冪;
		global 下位冪;
		global 至大指;
		global 巨位冪;
		global 至巨數;
		global 至小指;
		global 微位冪;
		global 至微數;
		global 位極差;
		global 浮點零;
		global 浮點一;
		global 試界;
		global 盤古;
		global 圓周率;
		global 倍圓周率;
		global 半圓周率;
		global 四分圓周率;
		global 自然常數;
		global 歐拉常數;
		global 黃金分割數;
		global 二之平方根;
		global 二之對數;
		global 十之對數;
		global 不可算數乎;
		global 下溢;
		global 上溢;
		global 除以零;
		global 不可算;
		global 求進冪;
		global 取位常數甲;
		global 取位常數乙;
		global 取位上溢限;
		global 分算常數;
		global 分算上溢限甲;
		global 分算上溢限乙;
		global 伏羲;
		global 取本位冪;
		global 取內鄰數;
		global 取外鄰數;
		global 分算;
		global 造雙數;
		global 雙數取反;
		global 以小加大得雙;
		global 相加得雙;
		global 加單於雙;
		global 以單減雙得單;
		global 加雙於雙;
		global 自乘得雙;
		global 相乘得雙;
		global 乘單於雙;
		global 雙數自乘;
		global 乘雙於雙;
		_ans236=甲[1-1];

		上甲=_ans236;
		_ans237=甲[2-1];

		下甲=_ans237;
		_ans238=乙[1-1];

		上乙=_ans238;
		_ans239=乙[2-1];

		下乙=_ans239;
		_ans240=相乘得雙(上甲)(上乙);

		丙=_ans240;
		_ans241=下乙*上甲;

		丁=_ans241;
		_ans242=上乙*下甲;
		_ans243=丁+_ans242;

		戊=_ans243;
		_ans244=丙[2-1];
		_ans245=_ans244+戊;
		_ans246=丙[1-1];
		_ans247=以小加大得雙(_ans245)(_ans246);
		return _ans247
	return _rand18;

求多項式=lambda _:0
def 求多項式 (式):
	def _rand19(甲):
		nonlocal 式;
		global 進制;
		global 退制;
		global 總算位;
		global 上位冪;
		global 下位冪;
		global 至大指;
		global 巨位冪;
		global 至巨數;
		global 至小指;
		global 微位冪;
		global 至微數;
		global 位極差;
		global 浮點零;
		global 浮點一;
		global 試界;
		global 盤古;
		global 圓周率;
		global 倍圓周率;
		global 半圓周率;
		global 四分圓周率;
		global 自然常數;
		global 歐拉常數;
		global 黃金分割數;
		global 二之平方根;
		global 二之對數;
		global 十之對數;
		global 不可算數乎;
		global 下溢;
		global 上溢;
		global 除以零;
		global 不可算;
		global 求進冪;
		global 取位常數甲;
		global 取位常數乙;
		global 取位上溢限;
		global 分算常數;
		global 分算上溢限甲;
		global 分算上溢限乙;
		global 伏羲;
		global 取本位冪;
		global 取內鄰數;
		global 取外鄰數;
		global 分算;
		global 造雙數;
		global 雙數取反;
		global 以小加大得雙;
		global 相加得雙;
		global 加單於雙;
		global 以單減雙得單;
		global 加雙於雙;
		global 自乘得雙;
		global 相乘得雙;
		global 乘單於雙;
		global 雙數自乘;
		global 乘雙於雙;
		global 求多項式;
		解=0
		_ans248=式.length if type(式) != str else len(式);
		引=_ans248;
		while (True):

			if 引==0:
				return 解

			_ans249=解*甲;

			乙=_ans249;
			_ans250=式[引-1];
			_ans251=乙+_ans250;

			解=_ans251;
			_ans252=引-1;

			引=_ans252;

	return _rand19;

""" "浮點移位。同Javascript之x * Math.pow(2, y), y is integer也。" """
浮點移位=lambda _:0
def 浮點移位 (本):
	def _rand20(位):
		nonlocal 本;
		global 進制;
		global 退制;
		global 總算位;
		global 上位冪;
		global 下位冪;
		global 至大指;
		global 巨位冪;
		global 至巨數;
		global 至小指;
		global 微位冪;
		global 至微數;
		global 位極差;
		global 浮點零;
		global 浮點一;
		global 試界;
		global 盤古;
		global 圓周率;
		global 倍圓周率;
		global 半圓周率;
		global 四分圓周率;
		global 自然常數;
		global 歐拉常數;
		global 黃金分割數;
		global 二之平方根;
		global 二之對數;
		global 十之對數;
		global 不可算數乎;
		global 下溢;
		global 上溢;
		global 除以零;
		global 不可算;
		global 求進冪;
		global 取位常數甲;
		global 取位常數乙;
		global 取位上溢限;
		global 分算常數;
		global 分算上溢限甲;
		global 分算上溢限乙;
		global 伏羲;
		global 取本位冪;
		global 取內鄰數;
		global 取外鄰數;
		global 分算;
		global 造雙數;
		global 雙數取反;
		global 以小加大得雙;
		global 相加得雙;
		global 加單於雙;
		global 以單減雙得單;
		global 加雙於雙;
		global 自乘得雙;
		global 相乘得雙;
		global 乘單於雙;
		global 雙數自乘;
		global 乘雙於雙;
		global 求多項式;
		global 浮點移位;
		""" "位正則進位。負則退位。" """

		if 位<=至大指:

			if 位>=至小指:
				_ans253=求進冪(位);
				_ans254=本*_ans253;
				return _ans254


		_ans255=不可算數乎(本);

		if _ans255:
			return 本

		_ans256=不可算數乎(位);

		if _ans256:
			return 位


		if 位>0:
			_ans257=位極差+2;

			限=_ans257;

			if 位<=限:
				_ans258=本;
				_ans259=位-至大指;
				_ans260=浮點移位(_ans258)(_ans259);
				_ans261=_ans260*巨位冪;
				return _ans261


			if 位<=至巨數:
				_ans262=本;
				_ans263=限-至大指;
				_ans264=浮點移位(_ans262)(_ans263);
				_ans265=_ans264*巨位冪;
				return _ans265


			if 本!=0:
				_ans266=正負(本);
				_ans267=上溢(_ans266);
				return _ans267

			else:
				_ans268=不可算();
				return _ans268


		else:
			_ans269=-2-位極差;

			限=_ans269;

			if 位>=限:
				_ans270=本;
				_ans271=位-至小指;
				_ans272=浮點移位(_ans270)(_ans271);
				_ans273=_ans272*微位冪;
				return _ans273

			_ans274=至巨數*-1;

			if 位>=_ans274:
				_ans275=本;
				_ans276=限-至小指;
				_ans277=浮點移位(_ans275)(_ans276);
				_ans278=_ans277*微位冪;
				return _ans278

			_ans279=絕對(本);

			if _ans279<=至巨數:
				_ans280=本*浮點零;
				return _ans280

			else:
				_ans281=不可算();
				return _ans281


	return _rand20;

""" "析浮點數。同Javascript之N/A也。" """
析浮點數=lambda _:0
def 析浮點數 (甲):
	global 進制;
	global 退制;
	global 總算位;
	global 上位冪;
	global 下位冪;
	global 至大指;
	global 巨位冪;
	global 至巨數;
	global 至小指;
	global 微位冪;
	global 至微數;
	global 位極差;
	global 浮點零;
	global 浮點一;
	global 試界;
	global 盤古;
	global 圓周率;
	global 倍圓周率;
	global 半圓周率;
	global 四分圓周率;
	global 自然常數;
	global 歐拉常數;
	global 黃金分割數;
	global 二之平方根;
	global 二之對數;
	global 十之對數;
	global 不可算數乎;
	global 下溢;
	global 上溢;
	global 除以零;
	global 不可算;
	global 求進冪;
	global 取位常數甲;
	global 取位常數乙;
	global 取位上溢限;
	global 分算常數;
	global 分算上溢限甲;
	global 分算上溢限乙;
	global 伏羲;
	global 取本位冪;
	global 取內鄰數;
	global 取外鄰數;
	global 分算;
	global 造雙數;
	global 雙數取反;
	global 以小加大得雙;
	global 相加得雙;
	global 加單於雙;
	global 以單減雙得單;
	global 加雙於雙;
	global 自乘得雙;
	global 相乘得雙;
	global 乘單於雙;
	global 雙數自乘;
	global 乘雙於雙;
	global 求多項式;
	global 浮點移位;
	global 析浮點數;
	""" "是術得一物。物有三數。曰符。曰位。曰本。符者。正負也。位者。進退位也。本者。本數也。" """
	""" "設計算機二進。若施是術於負六。乃得符負一。位二。本一又五分。" """
	造析=lambda _:0
	def 造析 (符):
		def _rand21(位):
			def _rand22(本):
				nonlocal 符;
				nonlocal 位;
				global 進制;
				global 退制;
				global 總算位;
				global 上位冪;
				global 下位冪;
				global 至大指;
				global 巨位冪;
				global 至巨數;
				global 至小指;
				global 微位冪;
				global 至微數;
				global 位極差;
				global 浮點零;
				global 浮點一;
				global 試界;
				global 盤古;
				global 圓周率;
				global 倍圓周率;
				global 半圓周率;
				global 四分圓周率;
				global 自然常數;
				global 歐拉常數;
				global 黃金分割數;
				global 二之平方根;
				global 二之對數;
				global 十之對數;
				global 不可算數乎;
				global 下溢;
				global 上溢;
				global 除以零;
				global 不可算;
				global 求進冪;
				global 取位常數甲;
				global 取位常數乙;
				global 取位上溢限;
				global 分算常數;
				global 分算上溢限甲;
				global 分算上溢限乙;
				global 伏羲;
				global 取本位冪;
				global 取內鄰數;
				global 取外鄰數;
				global 分算;
				global 造雙數;
				global 雙數取反;
				global 以小加大得雙;
				global 相加得雙;
				global 加單於雙;
				global 以單減雙得單;
				global 加雙於雙;
				global 自乘得雙;
				global 相乘得雙;
				global 乘單於雙;
				global 雙數自乘;
				global 乘雙於雙;
				global 求多項式;
				global 浮點移位;
				global 析浮點數;
				nonlocal 造析;
				析={}
				析={"符":符,"位":位,"本":本,};
				return 析
			return _rand22;
		return _rand21;

	乘=lambda _:0
	def 乘 (丙):
		def _rand23(丁):
			nonlocal 丙;
			global 進制;
			global 退制;
			global 總算位;
			global 上位冪;
			global 下位冪;
			global 至大指;
			global 巨位冪;
			global 至巨數;
			global 至小指;
			global 微位冪;
			global 至微數;
			global 位極差;
			global 浮點零;
			global 浮點一;
			global 試界;
			global 盤古;
			global 圓周率;
			global 倍圓周率;
			global 半圓周率;
			global 四分圓周率;
			global 自然常數;
			global 歐拉常數;
			global 黃金分割數;
			global 二之平方根;
			global 二之對數;
			global 十之對數;
			global 不可算數乎;
			global 下溢;
			global 上溢;
			global 除以零;
			global 不可算;
			global 求進冪;
			global 取位常數甲;
			global 取位常數乙;
			global 取位上溢限;
			global 分算常數;
			global 分算上溢限甲;
			global 分算上溢限乙;
			global 伏羲;
			global 取本位冪;
			global 取內鄰數;
			global 取外鄰數;
			global 分算;
			global 造雙數;
			global 雙數取反;
			global 以小加大得雙;
			global 相加得雙;
			global 加單於雙;
			global 以單減雙得單;
			global 加雙於雙;
			global 自乘得雙;
			global 相乘得雙;
			global 乘單於雙;
			global 雙數自乘;
			global 乘雙於雙;
			global 求多項式;
			global 浮點移位;
			global 析浮點數;
			nonlocal 造析;
			nonlocal 乘;
			_ans282=丁*丙;
			return _ans282
		return _rand23;

	_ans283=正負(甲);

	符=_ans283;
	_ans284=甲*符;

	乙=_ans284;

	if 甲==0:
		_ans285=符;
		_ans286=除以零(-1);
		_ans287=乙;
		_ans288=造析(_ans285)(_ans286)(_ans287);
		return _ans288

	_ans289=不可算數乎(甲);

	if _ans289:
		_ans290=符;
		_ans291=甲;
		_ans292=乙;
		_ans293=造析(_ans290)(_ans291)(_ans292);
		return _ans293


	if 乙>至巨數:
		_ans294=符;
		_ans295=乙;
		_ans296=乙;
		_ans297=造析(_ans294)(_ans295)(_ans296);
		return _ans297


	if 乙>=1:
		據=lambda _:0
		def 據 (丙):
			global 進制;
			global 退制;
			global 總算位;
			global 上位冪;
			global 下位冪;
			global 至大指;
			global 巨位冪;
			global 至巨數;
			global 至小指;
			global 微位冪;
			global 至微數;
			global 位極差;
			global 浮點零;
			global 浮點一;
			global 試界;
			global 盤古;
			global 圓周率;
			global 倍圓周率;
			global 半圓周率;
			global 四分圓周率;
			global 自然常數;
			global 歐拉常數;
			global 黃金分割數;
			global 二之平方根;
			global 二之對數;
			global 十之對數;
			global 不可算數乎;
			global 下溢;
			global 上溢;
			global 除以零;
			global 不可算;
			global 求進冪;
			global 取位常數甲;
			global 取位常數乙;
			global 取位上溢限;
			global 分算常數;
			global 分算上溢限甲;
			global 分算上溢限乙;
			global 伏羲;
			global 取本位冪;
			global 取內鄰數;
			global 取外鄰數;
			global 分算;
			global 造雙數;
			global 雙數取反;
			global 以小加大得雙;
			global 相加得雙;
			global 加單於雙;
			global 以單減雙得單;
			global 加雙於雙;
			global 自乘得雙;
			global 相乘得雙;
			global 乘單於雙;
			global 雙數自乘;
			global 乘雙於雙;
			global 求多項式;
			global 浮點移位;
			global 析浮點數;
			nonlocal 造析;
			nonlocal 乘;
			nonlocal 據;
			_ans298=丙*進制;

			if _ans298>乙:
				return True

			else:
				return False


		_ans299=至大指;
		_ans300=浮點一;
		_ans301=進制;
		_ans302=乘;
		_ans303=據;
		_ans304=試界(_ans299)(_ans300)(_ans301)(_ans302)(_ans303);

		位表=_ans304;
		_ans305=位表["引"];

		位=_ans305;
		_ans306=位表["實"];
		_ans307=乙/_ans306;

		本=_ans307;
		_ans308=符;
		_ans309=位;
		_ans310=本;
		_ans311=造析(_ans308)(_ans309)(_ans310);
		return _ans311

	else:
		據=lambda _:0
		def 據 (丙):
			global 進制;
			global 退制;
			global 總算位;
			global 上位冪;
			global 下位冪;
			global 至大指;
			global 巨位冪;
			global 至巨數;
			global 至小指;
			global 微位冪;
			global 至微數;
			global 位極差;
			global 浮點零;
			global 浮點一;
			global 試界;
			global 盤古;
			global 圓周率;
			global 倍圓周率;
			global 半圓周率;
			global 四分圓周率;
			global 自然常數;
			global 歐拉常數;
			global 黃金分割數;
			global 二之平方根;
			global 二之對數;
			global 十之對數;
			global 不可算數乎;
			global 下溢;
			global 上溢;
			global 除以零;
			global 不可算;
			global 求進冪;
			global 取位常數甲;
			global 取位常數乙;
			global 取位上溢限;
			global 分算常數;
			global 分算上溢限甲;
			global 分算上溢限乙;
			global 伏羲;
			global 取本位冪;
			global 取內鄰數;
			global 取外鄰數;
			global 分算;
			global 造雙數;
			global 雙數取反;
			global 以小加大得雙;
			global 相加得雙;
			global 加單於雙;
			global 以單減雙得單;
			global 加雙於雙;
			global 自乘得雙;
			global 相乘得雙;
			global 乘單於雙;
			global 雙數自乘;
			global 乘雙於雙;
			global 求多項式;
			global 浮點移位;
			global 析浮點數;
			nonlocal 造析;
			nonlocal 乘;
			nonlocal 據;
			nonlocal 據;

			if 丙<=乙:
				return True

			else:
				return False


		_ans312=總算位-至小指;
		_ans313=浮點一;
		_ans314=退制;
		_ans315=乘;
		_ans316=據;
		_ans317=試界(_ans312)(_ans313)(_ans314)(_ans315)(_ans316);

		位表=_ans317;
		_ans318=位表["引"];
		_ans319=0-_ans318;

		位=_ans319;
		_ans320=位表["實"];
		_ans321=乙/_ans320;

		本=_ans321;
		_ans322=符;
		_ans323=位;
		_ans324=本;
		_ans325=造析(_ans322)(_ans323)(_ans324);
		return _ans325


_ans326=上位冪/4;

整除大數限=_ans326;
""" "取底除。同Javascript之{ 商: Math.floor(x / y), 餘: x - y * quo }也。" """
取底除=lambda _:0
def 取底除 (實):
	def _rand24(法):
		nonlocal 實;
		global 進制;
		global 退制;
		global 總算位;
		global 上位冪;
		global 下位冪;
		global 至大指;
		global 巨位冪;
		global 至巨數;
		global 至小指;
		global 微位冪;
		global 至微數;
		global 位極差;
		global 浮點零;
		global 浮點一;
		global 試界;
		global 盤古;
		global 圓周率;
		global 倍圓周率;
		global 半圓周率;
		global 四分圓周率;
		global 自然常數;
		global 歐拉常數;
		global 黃金分割數;
		global 二之平方根;
		global 二之對數;
		global 十之對數;
		global 不可算數乎;
		global 下溢;
		global 上溢;
		global 除以零;
		global 不可算;
		global 求進冪;
		global 取位常數甲;
		global 取位常數乙;
		global 取位上溢限;
		global 分算常數;
		global 分算上溢限甲;
		global 分算上溢限乙;
		global 伏羲;
		global 取本位冪;
		global 取內鄰數;
		global 取外鄰數;
		global 分算;
		global 造雙數;
		global 雙數取反;
		global 以小加大得雙;
		global 相加得雙;
		global 加單於雙;
		global 以單減雙得單;
		global 加雙於雙;
		global 自乘得雙;
		global 相乘得雙;
		global 乘單於雙;
		global 雙數自乘;
		global 乘雙於雙;
		global 求多項式;
		global 浮點移位;
		global 析浮點數;
		global 取底除;
		_ans327=正負(法);

		法符=_ans327;
		_ans328=法*法符;

		法值=_ans328;
		_ans329=實*法符;

		乙=_ans329;
		_ans330=正負(乙);

		乙符=_ans330;
		_ans331=乙*乙符;

		實值=_ans331;
		_ans332=實值%法值;

		餘=_ans332;
		_ans333=實值-餘;
		_ans334=_ans333/法值;
		_ans335=取整(_ans334);

		商=_ans335;

		if 乙符<0:

			if 餘!=0:
				_ans336=-1-商;

				商=_ans336;
				_ans337=法值-餘;

				餘=_ans337;


		商餘={}
		商餘={"商":商,"餘":餘,};
		return 商餘
	return _rand24;

""" "取整除。同Javascript之{ 商: Math.round(x / y), 餘: x - y * quo }也。" """
取整除=lambda _:0
def 取整除 (實):
	def _rand25(法):
		nonlocal 實;
		global 進制;
		global 退制;
		global 總算位;
		global 上位冪;
		global 下位冪;
		global 至大指;
		global 巨位冪;
		global 至巨數;
		global 至小指;
		global 微位冪;
		global 至微數;
		global 位極差;
		global 浮點零;
		global 浮點一;
		global 試界;
		global 盤古;
		global 圓周率;
		global 倍圓周率;
		global 半圓周率;
		global 四分圓周率;
		global 自然常數;
		global 歐拉常數;
		global 黃金分割數;
		global 二之平方根;
		global 二之對數;
		global 十之對數;
		global 不可算數乎;
		global 下溢;
		global 上溢;
		global 除以零;
		global 不可算;
		global 求進冪;
		global 取位常數甲;
		global 取位常數乙;
		global 取位上溢限;
		global 分算常數;
		global 分算上溢限甲;
		global 分算上溢限乙;
		global 伏羲;
		global 取本位冪;
		global 取內鄰數;
		global 取外鄰數;
		global 分算;
		global 造雙數;
		global 雙數取反;
		global 以小加大得雙;
		global 相加得雙;
		global 加單於雙;
		global 以單減雙得單;
		global 加雙於雙;
		global 自乘得雙;
		global 相乘得雙;
		global 乘單於雙;
		global 雙數自乘;
		global 乘雙於雙;
		global 求多項式;
		global 浮點移位;
		global 析浮點數;
		global 取底除;
		global 取整除;
		_ans338=正負(法);

		法符=_ans338;
		_ans339=法*法符;

		法值=_ans339;
		_ans340=正負(實);

		實符=_ans340;
		_ans341=實*實符;

		實值=_ans341;
		_ans342=實符*法符;

		符=_ans342;
		_ans343=實值%法值;

		餘=_ans343;
		_ans344=實值-餘;
		_ans345=_ans344/法值;
		_ans346=取整(_ans345);

		商=_ans346;
		_ans347=法值/2;

		if 餘>=_ans347:
			_ans348=商+1;

			商=_ans348;
			_ans349=餘-法值;

			餘=_ans349;

		_ans350=商*符;

		商=_ans350;
		_ans351=餘*符;

		餘=_ans351;
		商餘={}
		商餘={"商":商,"餘":餘,};
		return 商餘
	return _rand25;

半圓周率密率=Ctnr()
_ans352=浮點移位(884279719003555)(-49);
半圓周率密率.push(_ans352)
_ans353=浮點移位(4967757600021511)(-106);
半圓周率密率.push(_ans353)
分四象=lambda _:0
def 分四象 (甲):
	def _rand26(上限):
		nonlocal 甲;
		global 進制;
		global 退制;
		global 總算位;
		global 上位冪;
		global 下位冪;
		global 至大指;
		global 巨位冪;
		global 至巨數;
		global 至小指;
		global 微位冪;
		global 至微數;
		global 位極差;
		global 浮點零;
		global 浮點一;
		global 試界;
		global 盤古;
		global 圓周率;
		global 倍圓周率;
		global 半圓周率;
		global 四分圓周率;
		global 自然常數;
		global 歐拉常數;
		global 黃金分割數;
		global 二之平方根;
		global 二之對數;
		global 十之對數;
		global 不可算數乎;
		global 下溢;
		global 上溢;
		global 除以零;
		global 不可算;
		global 求進冪;
		global 取位常數甲;
		global 取位常數乙;
		global 取位上溢限;
		global 分算常數;
		global 分算上溢限甲;
		global 分算上溢限乙;
		global 伏羲;
		global 取本位冪;
		global 取內鄰數;
		global 取外鄰數;
		global 分算;
		global 造雙數;
		global 雙數取反;
		global 以小加大得雙;
		global 相加得雙;
		global 加單於雙;
		global 以單減雙得單;
		global 加雙於雙;
		global 自乘得雙;
		global 相乘得雙;
		global 乘單於雙;
		global 雙數自乘;
		global 乘雙於雙;
		global 求多項式;
		global 浮點移位;
		global 析浮點數;
		global 取底除;
		global 取整除;
		global 半圓周率密率;
		global 分四象;
		""" "甲須為有限非零數。" """
		""" "術尚不精。當以極密率除之。" """
		_ans354=甲;
		_ans355=半圓周率密率[1-1];
		_ans356=取整除(_ans354)(_ans355);

		乙=_ans356;
		_ans357=乙["商"];

		商=_ans357;
		_ans358=乙["餘"];

		餘=_ans358;
		""" "半圓周率弧度即一象。" """
		_ans359=絕對(商);

		if _ans359>=整除大數限:
			""" "商甚大。或算位不足而謬之。" """
			移位=4
			_ans360=甲;
			_ans361=0-移位;
			_ans362=浮點移位(_ans360)(_ans361);
			_ans363=上限;
			_ans364=分四象(_ans362)(_ans363);
			_ans365=_ans364["角"];
			_ans366=移位;
			_ans367=浮點移位(_ans365)(_ans366);
			_ans368=上限;
			_ans369=分四象(_ans367)(_ans368);
			return _ans369

		_ans370=取底除(商)(4);
		_ans371=_ans370["餘"];

		象=_ans371;
		_ans372=半圓周率密率[2-1];
		_ans373=_ans372*商;
		_ans374=餘-_ans373;

		餘=_ans374;
		_ans375=絕對(餘);

		if _ans375>上限:
			_ans376=分四象(餘)(上限);

			解=_ans376;
			_ans377=解["象"];
			_ans378=象+_ans377;
			_ans379=4;
			_ans380=取底除(_ans378)(_ans379);
			_ans381=_ans380["餘"];

			解["象"]=_ans381;
			return 解

		else:
			解={}
			解={"角":餘,"象":象,};
			return 解

	return _rand26;

正餘弦角限=0.79
""" "略大於四十五度。" """
正弦多項式=Ctnr()
_ans382=-1/6;
正弦多項式.push(_ans382)
_ans383=1/120;
正弦多項式.push(_ans383)
_ans384=-1/5040;
正弦多項式.push(_ans384)
_ans385=1/362880;
正弦多項式.push(_ans385)
_ans386=-1/39916800;
正弦多項式.push(_ans386)
_ans387=1/6227020800;
正弦多項式.push(_ans387)
_ans388=-1/1307674368000;
正弦多項式.push(_ans388)
_ans389=1/355687428096000;
正弦多項式.push(_ans389)
餘弦多項式=Ctnr()
_ans390=-1/2;
餘弦多項式.push(_ans390)
_ans391=1/24;
餘弦多項式.push(_ans391)
_ans392=-1/720;
餘弦多項式.push(_ans392)
_ans393=1/40320;
餘弦多項式.push(_ans393)
_ans394=-1/3628800;
餘弦多項式.push(_ans394)
_ans395=1/479001600;
餘弦多項式.push(_ans395)
_ans396=-1/87178291200;
餘弦多項式.push(_ans396)
_ans397=1/20922789888000;
餘弦多項式.push(_ans397)
""" "正弦。同Javascript之Math.sin也。" """
正弦=lambda _:0
def 正弦 (甲):
	global 進制;
	global 退制;
	global 總算位;
	global 上位冪;
	global 下位冪;
	global 至大指;
	global 巨位冪;
	global 至巨數;
	global 至小指;
	global 微位冪;
	global 至微數;
	global 位極差;
	global 浮點零;
	global 浮點一;
	global 試界;
	global 盤古;
	global 圓周率;
	global 倍圓周率;
	global 半圓周率;
	global 四分圓周率;
	global 自然常數;
	global 歐拉常數;
	global 黃金分割數;
	global 二之平方根;
	global 二之對數;
	global 十之對數;
	global 不可算數乎;
	global 下溢;
	global 上溢;
	global 除以零;
	global 不可算;
	global 求進冪;
	global 取位常數甲;
	global 取位常數乙;
	global 取位上溢限;
	global 分算常數;
	global 分算上溢限甲;
	global 分算上溢限乙;
	global 伏羲;
	global 取本位冪;
	global 取內鄰數;
	global 取外鄰數;
	global 分算;
	global 造雙數;
	global 雙數取反;
	global 以小加大得雙;
	global 相加得雙;
	global 加單於雙;
	global 以單減雙得單;
	global 加雙於雙;
	global 自乘得雙;
	global 相乘得雙;
	global 乘單於雙;
	global 雙數自乘;
	global 乘雙於雙;
	global 求多項式;
	global 浮點移位;
	global 析浮點數;
	global 取底除;
	global 取整除;
	global 半圓周率密率;
	global 分四象;
	global 正餘弦角限;
	global 正弦多項式;
	global 餘弦多項式;
	global 正弦;
	""" "數小甚矣。乃得其身。否則以泰勒展開求之。復以週期性得其餘。" """
	_ans398=絕對(甲);

	乙=_ans398;

	if 乙<下位冪:
		return 甲


	if 乙<正餘弦角限:
		_ans399=甲*甲;

		二次冪=_ans399;
		_ans400=求多項式(正弦多項式)(二次冪);
		_ans401=_ans400*二次冪;
		_ans402=_ans401*甲;
		_ans403=甲+_ans402;
		return _ans403


	if 乙<=至巨數:
		_ans404=分四象(甲)(正餘弦角限);

		丙=_ans404;
		_ans405=丙["角"];

		丁=_ans405;
		_ans406=丙["象"];

		象=_ans406;
		_ans407=丁*丁;

		二次冪=_ans407;

		if 象==0:
			_ans408=求多項式(正弦多項式)(二次冪);
			_ans409=_ans408*二次冪;
			_ans410=_ans409*丁;
			_ans411=丁+_ans410;
			return _ans411


		if 象==1:
			_ans412=求多項式(餘弦多項式)(二次冪);
			_ans413=_ans412*二次冪;
			_ans414=1+_ans413;
			return _ans414


		if 象==2:
			_ans415=求多項式(正弦多項式)(二次冪);
			_ans416=_ans415*二次冪;
			_ans417=_ans416*丁;
			_ans418=丁+_ans417;
			_ans419=_ans418*-1;
			return _ans419


		if 象==3:
			_ans420=求多項式(餘弦多項式)(二次冪);
			_ans421=_ans420*二次冪;
			_ans422=-1-_ans421;
			return _ans422


	_ans423=不可算數乎(甲);

	if _ans423:
		return 甲

	_ans424=不可算();
	return _ans424

""" "餘弦。同Javascript之Math.cos也。" """
餘弦=lambda _:0
def 餘弦 (甲):
	global 進制;
	global 退制;
	global 總算位;
	global 上位冪;
	global 下位冪;
	global 至大指;
	global 巨位冪;
	global 至巨數;
	global 至小指;
	global 微位冪;
	global 至微數;
	global 位極差;
	global 浮點零;
	global 浮點一;
	global 試界;
	global 盤古;
	global 圓周率;
	global 倍圓周率;
	global 半圓周率;
	global 四分圓周率;
	global 自然常數;
	global 歐拉常數;
	global 黃金分割數;
	global 二之平方根;
	global 二之對數;
	global 十之對數;
	global 不可算數乎;
	global 下溢;
	global 上溢;
	global 除以零;
	global 不可算;
	global 求進冪;
	global 取位常數甲;
	global 取位常數乙;
	global 取位上溢限;
	global 分算常數;
	global 分算上溢限甲;
	global 分算上溢限乙;
	global 伏羲;
	global 取本位冪;
	global 取內鄰數;
	global 取外鄰數;
	global 分算;
	global 造雙數;
	global 雙數取反;
	global 以小加大得雙;
	global 相加得雙;
	global 加單於雙;
	global 以單減雙得單;
	global 加雙於雙;
	global 自乘得雙;
	global 相乘得雙;
	global 乘單於雙;
	global 雙數自乘;
	global 乘雙於雙;
	global 求多項式;
	global 浮點移位;
	global 析浮點數;
	global 取底除;
	global 取整除;
	global 半圓周率密率;
	global 分四象;
	global 正餘弦角限;
	global 正弦多項式;
	global 餘弦多項式;
	global 正弦;
	global 餘弦;
	""" "餘弦者。蓋正弦之變化所得。" """
	_ans425=絕對(甲);

	乙=_ans425;

	if 乙<下位冪:
		return 1


	if 乙<正餘弦角限:
		_ans426=甲*甲;

		二次冪=_ans426;
		_ans427=求多項式(餘弦多項式)(二次冪);
		_ans428=_ans427*二次冪;
		_ans429=_ans428+1;
		return _ans429


	if 乙<=至巨數:
		_ans430=分四象(甲)(正餘弦角限);

		丙=_ans430;
		_ans431=丙["角"];

		丁=_ans431;
		_ans432=丙["象"];

		象=_ans432;
		_ans433=丁*丁;

		二次冪=_ans433;

		if 象==0:
			_ans434=求多項式(餘弦多項式)(二次冪);
			_ans435=_ans434*二次冪;
			_ans436=1+_ans435;
			return _ans436


		if 象==1:
			_ans437=求多項式(正弦多項式)(二次冪);
			_ans438=_ans437*二次冪;
			_ans439=_ans438*丁;
			_ans440=丁+_ans439;
			_ans441=_ans440*-1;
			return _ans441


		if 象==2:
			_ans442=求多項式(餘弦多項式)(二次冪);
			_ans443=_ans442*二次冪;
			_ans444=-1-_ans443;
			return _ans444


		if 象==3:
			_ans445=求多項式(正弦多項式)(二次冪);
			_ans446=_ans445*二次冪;
			_ans447=_ans446*丁;
			_ans448=丁+_ans447;
			return _ans448


	_ans449=不可算數乎(甲);

	if _ans449:
		return 甲

	_ans450=不可算();
	return _ans450

反正弦多項式=Ctnr()
反正弦多項式.push(0.16666666666666646)
反正弦多項式.push(0.075000000000231853)
反正弦多項式.push(0.044642857099518776)
反正弦多項式.push(0.030381947612588188)
反正弦多項式.push(0.022372039724067996)
反正弦多項式.push(0.017355408429699168)
反正弦多項式.push(0.01392791627807614)
反正弦多項式.push(0.011888530510538809)
反正弦多項式.push(0.0077401244180669033)
反正弦多項式.push(0.016223422623182562)
反正弦多項式.push(-0.01106652157807397)
反正弦多項式.push(0.028400749201451962)
""" "反正弦。同Javascript之Math.asin也。" """
反正弦=lambda _:0
def 反正弦 (甲):
	global 進制;
	global 退制;
	global 總算位;
	global 上位冪;
	global 下位冪;
	global 至大指;
	global 巨位冪;
	global 至巨數;
	global 至小指;
	global 微位冪;
	global 至微數;
	global 位極差;
	global 浮點零;
	global 浮點一;
	global 試界;
	global 盤古;
	global 圓周率;
	global 倍圓周率;
	global 半圓周率;
	global 四分圓周率;
	global 自然常數;
	global 歐拉常數;
	global 黃金分割數;
	global 二之平方根;
	global 二之對數;
	global 十之對數;
	global 不可算數乎;
	global 下溢;
	global 上溢;
	global 除以零;
	global 不可算;
	global 求進冪;
	global 取位常數甲;
	global 取位常數乙;
	global 取位上溢限;
	global 分算常數;
	global 分算上溢限甲;
	global 分算上溢限乙;
	global 伏羲;
	global 取本位冪;
	global 取內鄰數;
	global 取外鄰數;
	global 分算;
	global 造雙數;
	global 雙數取反;
	global 以小加大得雙;
	global 相加得雙;
	global 加單於雙;
	global 以單減雙得單;
	global 加雙於雙;
	global 自乘得雙;
	global 相乘得雙;
	global 乘單於雙;
	global 雙數自乘;
	global 乘雙於雙;
	global 求多項式;
	global 浮點移位;
	global 析浮點數;
	global 取底除;
	global 取整除;
	global 半圓周率密率;
	global 分四象;
	global 正餘弦角限;
	global 正弦多項式;
	global 餘弦多項式;
	global 正弦;
	global 餘弦;
	global 反正弦多項式;
	global 反正弦;
	""" "小於五分者。以多項式求之。其餘以三角恆等式變化可得。" """
	_ans451=正負(甲);

	符=_ans451;
	_ans452=甲*符;

	乙=_ans452;
	非常=True

	if 乙>0:

		if 乙<=1:

			非常=False;



	if 非常:

		if 甲==0:
			return 甲

		_ans453=不可算數乎(甲);

		if _ans453:
			return 甲

		_ans454=不可算();
		return _ans454


	if 乙>0.5:
		_ans455=1-乙;
		_ans456=_ans455/2;

		丙=_ans456;
		_ans457=平方根(丙);
		_ans458=_ans457*2;

		丁=_ans458;
		_ans459=求多項式(反正弦多項式)(丙);
		_ans460=_ans459*丙;
		_ans461=_ans460*丁;
		_ans462=_ans461+丁;

		戊=_ans462;
		_ans463=半圓周率密率[2-1];
		_ans464=_ans463-戊;

		己=_ans464;
		_ans465=半圓周率密率[1-1];
		_ans466=己+_ans465;
		_ans467=_ans466*符;
		return _ans467

	else:
		_ans468=乙*乙;

		丙=_ans468;
		_ans469=求多項式(反正弦多項式)(丙);
		_ans470=_ans469*丙;
		_ans471=_ans470*甲;
		_ans472=甲+_ans471;
		return _ans472


""" "反餘弦。同Javascript之Math.acos也。" """
反餘弦=lambda _:0
def 反餘弦 (甲):
	global 進制;
	global 退制;
	global 總算位;
	global 上位冪;
	global 下位冪;
	global 至大指;
	global 巨位冪;
	global 至巨數;
	global 至小指;
	global 微位冪;
	global 至微數;
	global 位極差;
	global 浮點零;
	global 浮點一;
	global 試界;
	global 盤古;
	global 圓周率;
	global 倍圓周率;
	global 半圓周率;
	global 四分圓周率;
	global 自然常數;
	global 歐拉常數;
	global 黃金分割數;
	global 二之平方根;
	global 二之對數;
	global 十之對數;
	global 不可算數乎;
	global 下溢;
	global 上溢;
	global 除以零;
	global 不可算;
	global 求進冪;
	global 取位常數甲;
	global 取位常數乙;
	global 取位上溢限;
	global 分算常數;
	global 分算上溢限甲;
	global 分算上溢限乙;
	global 伏羲;
	global 取本位冪;
	global 取內鄰數;
	global 取外鄰數;
	global 分算;
	global 造雙數;
	global 雙數取反;
	global 以小加大得雙;
	global 相加得雙;
	global 加單於雙;
	global 以單減雙得單;
	global 加雙於雙;
	global 自乘得雙;
	global 相乘得雙;
	global 乘單於雙;
	global 雙數自乘;
	global 乘雙於雙;
	global 求多項式;
	global 浮點移位;
	global 析浮點數;
	global 取底除;
	global 取整除;
	global 半圓周率密率;
	global 分四象;
	global 正餘弦角限;
	global 正弦多項式;
	global 餘弦多項式;
	global 正弦;
	global 餘弦;
	global 反正弦多項式;
	global 反正弦;
	global 反餘弦;
	""" "反餘弦者。蓋反正弦之變化所得。" """
	_ans473=絕對(甲);

	乙=_ans473;
	非常=True

	if 乙<=1:

		非常=False;


	if 非常:
		_ans474=不可算數乎(甲);

		if _ans474:
			return 甲

		_ans475=不可算();
		return _ans475


	if 乙>0.5:
		_ans476=1-乙;
		_ans477=_ans476/2;

		丙=_ans477;
		_ans478=平方根(丙);
		_ans479=_ans478*2;

		丁=_ans479;
		_ans480=求多項式(反正弦多項式)(丙);
		_ans481=_ans480*丙;
		_ans482=_ans481*丁;
		_ans483=_ans482+丁;

		戊=_ans483;

		if 甲>0:
			return 戊

		else:
			_ans484=半圓周率密率[2-1];
			_ans485=_ans484*2;
			_ans486=_ans485-戊;

			己=_ans486;
			_ans487=半圓周率密率[1-1];
			_ans488=_ans487*2;
			_ans489=己+_ans488;
			return _ans489


	else:
		_ans490=乙*乙;

		丙=_ans490;
		_ans491=求多項式(反正弦多項式)(丙);
		_ans492=_ans491*丙;
		_ans493=_ans492*甲;
		_ans494=甲+_ans493;

		戊=_ans494;
		_ans495=半圓周率密率[2-1];
		_ans496=_ans495-戊;

		己=_ans496;
		_ans497=半圓周率密率[1-1];
		_ans498=己+_ans497;
		return _ans498


""" "正切。同Javascript之Math.tan也。" """
正切=lambda _:0
def 正切 (甲):
	global 進制;
	global 退制;
	global 總算位;
	global 上位冪;
	global 下位冪;
	global 至大指;
	global 巨位冪;
	global 至巨數;
	global 至小指;
	global 微位冪;
	global 至微數;
	global 位極差;
	global 浮點零;
	global 浮點一;
	global 試界;
	global 盤古;
	global 圓周率;
	global 倍圓周率;
	global 半圓周率;
	global 四分圓周率;
	global 自然常數;
	global 歐拉常數;
	global 黃金分割數;
	global 二之平方根;
	global 二之對數;
	global 十之對數;
	global 不可算數乎;
	global 下溢;
	global 上溢;
	global 除以零;
	global 不可算;
	global 求進冪;
	global 取位常數甲;
	global 取位常數乙;
	global 取位上溢限;
	global 分算常數;
	global 分算上溢限甲;
	global 分算上溢限乙;
	global 伏羲;
	global 取本位冪;
	global 取內鄰數;
	global 取外鄰數;
	global 分算;
	global 造雙數;
	global 雙數取反;
	global 以小加大得雙;
	global 相加得雙;
	global 加單於雙;
	global 以單減雙得單;
	global 加雙於雙;
	global 自乘得雙;
	global 相乘得雙;
	global 乘單於雙;
	global 雙數自乘;
	global 乘雙於雙;
	global 求多項式;
	global 浮點移位;
	global 析浮點數;
	global 取底除;
	global 取整除;
	global 半圓周率密率;
	global 分四象;
	global 正餘弦角限;
	global 正弦多項式;
	global 餘弦多項式;
	global 正弦;
	global 餘弦;
	global 反正弦多項式;
	global 反正弦;
	global 反餘弦;
	global 正切;
	""" "數小甚矣。乃得其身。其餘或以三角恆等式。或以週期性可得。" """
	_ans499=絕對(甲);

	乙=_ans499;

	if 乙<下位冪:
		return 甲


	if 乙<正餘弦角限:
		_ans500=甲*甲;

		二次冪=_ans500;
		_ans501=求多項式(正弦多項式)(二次冪);
		_ans502=_ans501*二次冪;
		_ans503=_ans502*甲;
		_ans504=甲+_ans503;

		勾=_ans504;
		_ans505=求多項式(餘弦多項式)(二次冪);
		_ans506=_ans505*二次冪;
		_ans507=_ans506+1;

		股=_ans507;
		_ans508=勾/股;
		return _ans508


	if 乙<=至巨數:
		_ans509=分四象(甲)(正餘弦角限);

		丙=_ans509;
		_ans510=丙["角"];

		丁=_ans510;
		_ans511=丙["象"];

		象=_ans511;
		_ans512=丁*丁;

		二次冪=_ans512;

		if 象==0:
			_ans513=求多項式(正弦多項式)(二次冪);
			_ans514=_ans513*二次冪;
			_ans515=_ans514*丁;
			_ans516=丁+_ans515;

			勾=_ans516;
			_ans517=求多項式(餘弦多項式)(二次冪);
			_ans518=_ans517*二次冪;
			_ans519=1+_ans518;

			股=_ans519;
			_ans520=勾/股;
			return _ans520


		if 象==1:
			_ans521=求多項式(餘弦多項式)(二次冪);
			_ans522=_ans521*二次冪;
			_ans523=1+_ans522;

			勾=_ans523;
			_ans524=求多項式(正弦多項式)(二次冪);
			_ans525=_ans524*二次冪;
			_ans526=_ans525*丁;
			_ans527=丁+_ans526;
			_ans528=_ans527*-1;

			股=_ans528;
			_ans529=勾/股;
			return _ans529


		if 象==2:
			_ans530=求多項式(正弦多項式)(二次冪);
			_ans531=_ans530*二次冪;
			_ans532=_ans531*丁;
			_ans533=丁+_ans532;
			_ans534=_ans533*-1;

			勾=_ans534;
			_ans535=求多項式(餘弦多項式)(二次冪);
			_ans536=_ans535*二次冪;
			_ans537=-1-_ans536;

			股=_ans537;
			_ans538=勾/股;
			return _ans538


		if 象==3:
			_ans539=求多項式(餘弦多項式)(二次冪);
			_ans540=_ans539*二次冪;
			_ans541=-1-_ans540;

			勾=_ans541;
			_ans542=求多項式(正弦多項式)(二次冪);
			_ans543=_ans542*二次冪;
			_ans544=_ans543*丁;
			_ans545=丁+_ans544;

			股=_ans545;
			_ans546=勾/股;
			return _ans546


	_ans547=不可算數乎(甲);

	if _ans547:
		return 甲

	_ans548=不可算();
	return _ans548

反正切多項式=Ctnr()
反正切多項式.push(-0.33333333333333326)
反正切多項式.push(0.19999999999992268)
反正切多項式.push(-0.14285714284210957)
反正切多項式.push(0.11111110996568103)
反正切多項式.push(-0.090909045736192809)
反正切多項式.push(0.076922022110850696)
反正切多項式.push(-0.066650962737093755)
反正切多項式.push(0.058668191246172313)
反正切多項式.push(-0.051590554508407487)
反正切多項式.push(0.04288146123573456)
反正切多項式.push(-0.029030170160975751)
反正切多項式.push(0.011208491193087792)
""" "反正切。同Javascript之Math.atan也。" """
反正切=lambda _:0
def 反正切 (甲):
	global 進制;
	global 退制;
	global 總算位;
	global 上位冪;
	global 下位冪;
	global 至大指;
	global 巨位冪;
	global 至巨數;
	global 至小指;
	global 微位冪;
	global 至微數;
	global 位極差;
	global 浮點零;
	global 浮點一;
	global 試界;
	global 盤古;
	global 圓周率;
	global 倍圓周率;
	global 半圓周率;
	global 四分圓周率;
	global 自然常數;
	global 歐拉常數;
	global 黃金分割數;
	global 二之平方根;
	global 二之對數;
	global 十之對數;
	global 不可算數乎;
	global 下溢;
	global 上溢;
	global 除以零;
	global 不可算;
	global 求進冪;
	global 取位常數甲;
	global 取位常數乙;
	global 取位上溢限;
	global 分算常數;
	global 分算上溢限甲;
	global 分算上溢限乙;
	global 伏羲;
	global 取本位冪;
	global 取內鄰數;
	global 取外鄰數;
	global 分算;
	global 造雙數;
	global 雙數取反;
	global 以小加大得雙;
	global 相加得雙;
	global 加單於雙;
	global 以單減雙得單;
	global 加雙於雙;
	global 自乘得雙;
	global 相乘得雙;
	global 乘單於雙;
	global 雙數自乘;
	global 乘雙於雙;
	global 求多項式;
	global 浮點移位;
	global 析浮點數;
	global 取底除;
	global 取整除;
	global 半圓周率密率;
	global 分四象;
	global 正餘弦角限;
	global 正弦多項式;
	global 餘弦多項式;
	global 正弦;
	global 餘弦;
	global 反正弦多項式;
	global 反正弦;
	global 反餘弦;
	global 正切;
	global 反正切多項式;
	global 反正切;
	""" "小於五分者。以多項式求之。其餘以三角恆等式變化可得。" """
	_ans549=正負(甲);

	符=_ans549;
	_ans550=甲*符;

	乙=_ans550;
	非常=True

	if 乙>0:

		if 乙<=至巨數:

			非常=False;



	if 非常:

		if 乙==0:
			return 甲


		if 乙>至巨數:
			_ans551=半圓周率*符;
			return _ans551

		return 甲


	if 乙<0.5:
		_ans552=乙*乙;

		丙=_ans552;
		_ans553=求多項式(反正切多項式)(丙);
		_ans554=_ans553*丙;
		_ans555=_ans554*甲;
		_ans556=甲+_ans555;
		return _ans556

		if 乙>2:
			_ans557=1/乙;

			丁=_ans557;
			_ans558=丁*丁;

			丙=_ans558;
			_ans559=求多項式(反正切多項式)(丙);
			_ans560=_ans559*丙;
			_ans561=_ans560*丁;
			_ans562=丁+_ans561;

			戊=_ans562;
			_ans563=半圓周率密率[2-1];
			_ans564=_ans563-戊;

			己=_ans564;
			_ans565=半圓周率密率[1-1];
			_ans566=己+_ans565;
			_ans567=_ans566*符;
			return _ans567

		else:
			_ans568=乙-1;

			庚=_ans568;
			_ans569=1+乙;
			_ans570=庚/_ans569;

			丁=_ans570;
			_ans571=丁*丁;

			丙=_ans571;
			_ans572=求多項式(反正切多項式)(丙);
			_ans573=_ans572*丙;
			_ans574=_ans573*丁;
			_ans575=丁+_ans574;

			戊=_ans575;
			_ans576=半圓周率密率[2-1];
			_ans577=_ans576/2;
			_ans578=戊+_ans577;

			己=_ans578;
			_ans579=半圓周率密率[1-1];
			_ans580=_ans579/2;
			_ans581=己+_ans580;
			_ans582=_ans581*符;
			return _ans582

	return undefined;

""" "勾股求角。同Javascript之Math.atan2也。" """
勾股求角=lambda _:0
def 勾股求角 (甲):
	def _rand27(乙):
		nonlocal 甲;
		global 進制;
		global 退制;
		global 總算位;
		global 上位冪;
		global 下位冪;
		global 至大指;
		global 巨位冪;
		global 至巨數;
		global 至小指;
		global 微位冪;
		global 至微數;
		global 位極差;
		global 浮點零;
		global 浮點一;
		global 試界;
		global 盤古;
		global 圓周率;
		global 倍圓周率;
		global 半圓周率;
		global 四分圓周率;
		global 自然常數;
		global 歐拉常數;
		global 黃金分割數;
		global 二之平方根;
		global 二之對數;
		global 十之對數;
		global 不可算數乎;
		global 下溢;
		global 上溢;
		global 除以零;
		global 不可算;
		global 求進冪;
		global 取位常數甲;
		global 取位常數乙;
		global 取位上溢限;
		global 分算常數;
		global 分算上溢限甲;
		global 分算上溢限乙;
		global 伏羲;
		global 取本位冪;
		global 取內鄰數;
		global 取外鄰數;
		global 分算;
		global 造雙數;
		global 雙數取反;
		global 以小加大得雙;
		global 相加得雙;
		global 加單於雙;
		global 以單減雙得單;
		global 加雙於雙;
		global 自乘得雙;
		global 相乘得雙;
		global 乘單於雙;
		global 雙數自乘;
		global 乘雙於雙;
		global 求多項式;
		global 浮點移位;
		global 析浮點數;
		global 取底除;
		global 取整除;
		global 半圓周率密率;
		global 分四象;
		global 正餘弦角限;
		global 正弦多項式;
		global 餘弦多項式;
		global 正弦;
		global 餘弦;
		global 反正弦多項式;
		global 反正弦;
		global 反餘弦;
		global 正切;
		global 反正切多項式;
		global 反正切;
		global 勾股求角;
		""" "反正切之分類討論也" """
		_ans583=絕對(甲);

		if _ans583>至巨數:
			_ans584=絕對(乙);

			if _ans584>至巨數:
				_ans585=正負(甲);
				_ans586=正負(乙);
				_ans587=勾股求角(_ans585)(_ans586);
				return _ans587



		if 乙==0:

			if 甲>0:
				return 半圓周率


			if 甲<0:
				_ans588=0-半圓周率;
				return _ans588

			return 0

		_ans589=甲/乙;
		_ans590=反正切(_ans589);

		丙=_ans590;

		if 乙>0:
			return 丙


		if 甲>=0:
			_ans591=丙+圓周率;
			return _ans591

		_ans592=丙-圓周率;
		return _ans592
	return _rand27;

_ans593=5062973/2097152;

勾股求弦常數上=_ans593;
勾股求弦常數下=-9.500605534182331127579030192143032812462e-8
""" "加二之平方根於一也。" """
""" "勾股求弦。同Javascript之Math.hypot也。" """
勾股求弦=lambda _:0
def 勾股求弦 (勾):
	def _rand28(股):
		nonlocal 勾;
		global 進制;
		global 退制;
		global 總算位;
		global 上位冪;
		global 下位冪;
		global 至大指;
		global 巨位冪;
		global 至巨數;
		global 至小指;
		global 微位冪;
		global 至微數;
		global 位極差;
		global 浮點零;
		global 浮點一;
		global 試界;
		global 盤古;
		global 圓周率;
		global 倍圓周率;
		global 半圓周率;
		global 四分圓周率;
		global 自然常數;
		global 歐拉常數;
		global 黃金分割數;
		global 二之平方根;
		global 二之對數;
		global 十之對數;
		global 不可算數乎;
		global 下溢;
		global 上溢;
		global 除以零;
		global 不可算;
		global 求進冪;
		global 取位常數甲;
		global 取位常數乙;
		global 取位上溢限;
		global 分算常數;
		global 分算上溢限甲;
		global 分算上溢限乙;
		global 伏羲;
		global 取本位冪;
		global 取內鄰數;
		global 取外鄰數;
		global 分算;
		global 造雙數;
		global 雙數取反;
		global 以小加大得雙;
		global 相加得雙;
		global 加單於雙;
		global 以單減雙得單;
		global 加雙於雙;
		global 自乘得雙;
		global 相乘得雙;
		global 乘單於雙;
		global 雙數自乘;
		global 乘雙於雙;
		global 求多項式;
		global 浮點移位;
		global 析浮點數;
		global 取底除;
		global 取整除;
		global 半圓周率密率;
		global 分四象;
		global 正餘弦角限;
		global 正弦多項式;
		global 餘弦多項式;
		global 正弦;
		global 餘弦;
		global 反正弦多項式;
		global 反正弦;
		global 反餘弦;
		global 正切;
		global 反正切多項式;
		global 反正切;
		global 勾股求角;
		global 勾股求弦常數下;
		global 勾股求弦;
		_ans594=絕對(勾);

		甲=_ans594;
		_ans595=絕對(股);

		乙=_ans595;

		if 甲==0:
			return 乙


		if 乙==0:
			return 甲


		if 甲>至巨數:
			return 甲


		if 乙>至巨數:
			return 乙

		_ans596=不可算數乎(甲);

		if _ans596:
			return 甲

		_ans597=不可算數乎(乙);

		if _ans597:
			return 乙


		if 乙>甲:
			借=甲

			甲=乙;

			乙=借;

		_ans598=甲-乙;

		丙=_ans598;

		if 丙==甲:
			return 甲

			if 丙>乙:
				_ans599=甲/乙;

				丁=_ans599;
				_ans600=丁*丁;
				_ans601=1+_ans600;
				_ans602=平方根(_ans601);
				_ans603=丁+_ans602;
				_ans604=乙/_ans603;
				_ans605=甲+_ans604;
				return _ans605

			else:
				_ans606=丙/乙;

				戊=_ans606;
				_ans607=2+戊;
				_ans608=_ans607*戊;

				己=_ans608;
				_ans609=2+己;
				_ans610=平方根(_ans609);
				_ans611=二之平方根+_ans610;
				_ans612=己/_ans611;

				庚=_ans612;
				_ans613=勾股求弦常數下+庚;
				_ans614=戊+_ans613;
				_ans615=勾股求弦常數上+_ans614;
				_ans616=乙/_ans615;
				_ans617=甲+_ans616;
				return _ans617

		return _rand28;
	return undefined;

_ans618=1453635/2097152;

二之對數上=_ans618;
二之對數下=-1.90465429995776787854182343192449986564e-9
對數多項式甲=Ctnr()
_ans619=1/3;
對數多項式甲.push(_ans619)
_ans620=1/5;
對數多項式甲.push(_ans620)
_ans621=1/7;
對數多項式甲.push(_ans621)
_ans622=1/9;
對數多項式甲.push(_ans622)
_ans623=1/11;
對數多項式甲.push(_ans623)
_ans624=1/13;
對數多項式甲.push(_ans624)
_ans625=1/15;
對數多項式甲.push(_ans625)
_ans626=1/17;
對數多項式甲.push(_ans626)
_ans627=1/19;
對數多項式甲.push(_ans627)
""" " x^2 * f(x^2) = atanh(x)/x - 1 " """
""" "對數。同Javascript之Math.log也。" """
對數=lambda _:0
def 對數 (甲):
	global 進制;
	global 退制;
	global 總算位;
	global 上位冪;
	global 下位冪;
	global 至大指;
	global 巨位冪;
	global 至巨數;
	global 至小指;
	global 微位冪;
	global 至微數;
	global 位極差;
	global 浮點零;
	global 浮點一;
	global 試界;
	global 盤古;
	global 圓周率;
	global 倍圓周率;
	global 半圓周率;
	global 四分圓周率;
	global 自然常數;
	global 歐拉常數;
	global 黃金分割數;
	global 二之平方根;
	global 二之對數;
	global 十之對數;
	global 不可算數乎;
	global 下溢;
	global 上溢;
	global 除以零;
	global 不可算;
	global 求進冪;
	global 取位常數甲;
	global 取位常數乙;
	global 取位上溢限;
	global 分算常數;
	global 分算上溢限甲;
	global 分算上溢限乙;
	global 伏羲;
	global 取本位冪;
	global 取內鄰數;
	global 取外鄰數;
	global 分算;
	global 造雙數;
	global 雙數取反;
	global 以小加大得雙;
	global 相加得雙;
	global 加單於雙;
	global 以單減雙得單;
	global 加雙於雙;
	global 自乘得雙;
	global 相乘得雙;
	global 乘單於雙;
	global 雙數自乘;
	global 乘雙於雙;
	global 求多項式;
	global 浮點移位;
	global 析浮點數;
	global 取底除;
	global 取整除;
	global 半圓周率密率;
	global 分四象;
	global 正餘弦角限;
	global 正弦多項式;
	global 餘弦多項式;
	global 正弦;
	global 餘弦;
	global 反正弦多項式;
	global 反正弦;
	global 反餘弦;
	global 正切;
	global 反正切多項式;
	global 反正切;
	global 勾股求角;
	global 勾股求弦常數下;
	global 勾股求弦;
	global 二之對數下;
	global 對數多項式甲;
	global 對數;
	""" "自然對數。" """
	非常=True

	if 甲>0:

		if 甲<=至巨數:

			非常=False;



	if 非常:

		if 甲==0:
			_ans628=除以零(-1);
			return _ans628


		if 甲<0:
			_ans629=不可算();
			return _ans629

		return 甲

	""" "以對數屬性佐泰勒展開" """
	_ans630=析浮點數(甲);

	析甲=_ans630;
	_ans631=析甲["位"];

	位=_ans631;
	_ans632=析甲["本"];

	本=_ans632;

	if 本>二之平方根:
		_ans633=位+1;

		位=_ans633;
		_ans634=本/2;

		本=_ans634;

	_ans635=位*二之對數;

	乙=_ans635;
	_ans636=本-1;

	分子=_ans636;
	_ans637=本+1;
	_ans638=分子/_ans637;

	丙=_ans638;
	_ans639=丙*丙;

	二次冪=_ans639;
	_ans640=求多項式(對數多項式甲)(二次冪);
	_ans641=_ans640*二次冪;
	_ans642=_ans641*丙;
	_ans643=丙+_ans642;
	_ans644=_ans643*2;
	_ans645=_ans644+乙;
	return _ans645

_ans646=至大指+2;
_ans647=_ans646*二之對數;

指數上溢限=_ans647;
_ans648=至小指-總算位;
_ans649=_ans648-1;
_ans650=_ans649*二之對數;

指數下溢限=_ans650;
指數多項式甲=Ctnr()
_ans651=1/3;
指數多項式甲.push(_ans651)
_ans652=-1/45;
指數多項式甲.push(_ans652)
_ans653=2/945;
指數多項式甲.push(_ans653)
_ans654=-1/4725;
指數多項式甲.push(_ans654)
_ans655=2/93555;
指數多項式甲.push(_ans655)
_ans656=-1382/638512875;
指數多項式甲.push(_ans656)
""" " x^2 * f(x^2) = x/tanh(x) - 1 " """
""" "指數。同Javascript之Math.exp也。" """
指數=lambda _:0
def 指數 (甲):
	global 進制;
	global 退制;
	global 總算位;
	global 上位冪;
	global 下位冪;
	global 至大指;
	global 巨位冪;
	global 至巨數;
	global 至小指;
	global 微位冪;
	global 至微數;
	global 位極差;
	global 浮點零;
	global 浮點一;
	global 試界;
	global 盤古;
	global 圓周率;
	global 倍圓周率;
	global 半圓周率;
	global 四分圓周率;
	global 自然常數;
	global 歐拉常數;
	global 黃金分割數;
	global 二之平方根;
	global 二之對數;
	global 十之對數;
	global 不可算數乎;
	global 下溢;
	global 上溢;
	global 除以零;
	global 不可算;
	global 求進冪;
	global 取位常數甲;
	global 取位常數乙;
	global 取位上溢限;
	global 分算常數;
	global 分算上溢限甲;
	global 分算上溢限乙;
	global 伏羲;
	global 取本位冪;
	global 取內鄰數;
	global 取外鄰數;
	global 分算;
	global 造雙數;
	global 雙數取反;
	global 以小加大得雙;
	global 相加得雙;
	global 加單於雙;
	global 以單減雙得單;
	global 加雙於雙;
	global 自乘得雙;
	global 相乘得雙;
	global 乘單於雙;
	global 雙數自乘;
	global 乘雙於雙;
	global 求多項式;
	global 浮點移位;
	global 析浮點數;
	global 取底除;
	global 取整除;
	global 半圓周率密率;
	global 分四象;
	global 正餘弦角限;
	global 正弦多項式;
	global 餘弦多項式;
	global 正弦;
	global 餘弦;
	global 反正弦多項式;
	global 反正弦;
	global 反餘弦;
	global 正切;
	global 反正切多項式;
	global 反正切;
	global 勾股求角;
	global 勾股求弦常數下;
	global 勾股求弦;
	global 二之對數下;
	global 對數多項式甲;
	global 對數;
	global 指數多項式甲;
	global 指數;
	""" "自然指數。" """
	非常=True

	if 甲<指數上溢限:

		if 甲>指數下溢限:

			非常=False;



	if 非常:
		_ans657=不可算數乎(甲);

		if _ans657:
			return 甲


		if 甲>0:

			if 甲>至巨數:
				return 甲

			else:
				_ans658=上溢(1);
				return _ans658


		else:
			_ans659=至巨數*-1;

			if 甲<_ans659:
				return 浮點零

			else:
				_ans660=下溢(1);
				return _ans660



	_ans661=甲/二之對數;
	_ans662=取整(_ans661);

	移位數=_ans662;
	_ans663=移位數*二之對數上;
	_ans664=甲-_ans663;

	乙=_ans664;
	_ans665=移位數*二之對數下;
	_ans666=乙-_ans665;

	丙=_ans666;
	""" "除二之對數於甲。其餘者丙。以密率求之。" """
	_ans667=丙/2;

	丁=_ans667;
	_ans668=丁*丁;

	戊=_ans668;
	_ans669=求多項式(指數多項式甲)(戊);
	_ans670=_ans669*戊;
	_ans671=丁-_ans670;

	己=_ans671;
	_ans672=1-己;
	_ans673=丙/_ans672;
	_ans674=1+_ans673;

	庚=_ans674;
	_ans675=浮點移位(庚)(移位數);
	return _ans675

對數多項式乙上=Ctnr()
對數多項式乙上.push(0.33331724229478565391105,0.20431337379679007093536)
對數多項式乙下=Ctnr()
對數多項式乙下.push(1.6091038547679431e-5,-0.0043133737967901067,0.14285714285717646,0.11111111109925075,0.090909092988218018,0.076922873303695544,0.066678321857932515,0.058437264131467867,0.059443884378751484)
""" " x^2 * (f0(x^2) + f1(x^2)) = atanh(x)/x - 1 " """
正數之冪=lambda _:0
def 正數之冪 (底):
	def _rand29(指):
		nonlocal 底;
		global 進制;
		global 退制;
		global 總算位;
		global 上位冪;
		global 下位冪;
		global 至大指;
		global 巨位冪;
		global 至巨數;
		global 至小指;
		global 微位冪;
		global 至微數;
		global 位極差;
		global 浮點零;
		global 浮點一;
		global 試界;
		global 盤古;
		global 圓周率;
		global 倍圓周率;
		global 半圓周率;
		global 四分圓周率;
		global 自然常數;
		global 歐拉常數;
		global 黃金分割數;
		global 二之平方根;
		global 二之對數;
		global 十之對數;
		global 不可算數乎;
		global 下溢;
		global 上溢;
		global 除以零;
		global 不可算;
		global 求進冪;
		global 取位常數甲;
		global 取位常數乙;
		global 取位上溢限;
		global 分算常數;
		global 分算上溢限甲;
		global 分算上溢限乙;
		global 伏羲;
		global 取本位冪;
		global 取內鄰數;
		global 取外鄰數;
		global 分算;
		global 造雙數;
		global 雙數取反;
		global 以小加大得雙;
		global 相加得雙;
		global 加單於雙;
		global 以單減雙得單;
		global 加雙於雙;
		global 自乘得雙;
		global 相乘得雙;
		global 乘單於雙;
		global 雙數自乘;
		global 乘雙於雙;
		global 求多項式;
		global 浮點移位;
		global 析浮點數;
		global 取底除;
		global 取整除;
		global 半圓周率密率;
		global 分四象;
		global 正餘弦角限;
		global 正弦多項式;
		global 餘弦多項式;
		global 正弦;
		global 餘弦;
		global 反正弦多項式;
		global 反正弦;
		global 反餘弦;
		global 正切;
		global 反正切多項式;
		global 反正切;
		global 勾股求角;
		global 勾股求弦常數下;
		global 勾股求弦;
		global 二之對數下;
		global 對數多項式甲;
		global 對數;
		global 指數多項式甲;
		global 指數;
		global 對數多項式乙上;
		global 對數多項式乙下;
		global 正數之冪;
		""" "底為有限正數。指為有限數。" """
		""" "以下求底之對數。" """
		_ans676=析浮點數(底);

		析底=_ans676;
		_ans677=析底["位"];

		位=_ans677;
		_ans678=析底["本"];

		本=_ans678;

		if 本>二之平方根:
			_ans679=位+1;

			位=_ans679;
			_ans680=本/2;

			本=_ans680;

		_ans681=本-1;

		丙=_ans681;
		_ans682=本+1;

		丁=_ans682;
		_ans683=丙/丁;

		戊=_ans683;
		_ans684=戊;
		_ans685=戊;
		_ans686=本;
		_ans687=相乘得雙(_ans685)(_ans686);
		_ans688=加單於雙(_ans684)(_ans687);

		己=_ans688;
		_ans689=丙;
		_ans690=己;
		_ans691=以單減雙得單(_ans689)(_ans690);
		_ans692=_ans691*-1;
		_ans693=_ans692/丁;
		_ans694=戊;
		_ans695=以小加大得雙(_ans693)(_ans694);

		庚=_ans695;
		_ans696=雙數自乘(庚);

		辛=_ans696;
		_ans697=對數多項式乙下;
		_ans698=辛[1-1];
		_ans699=求多項式(_ans697)(_ans698);
		_ans700=對數多項式乙上[2-1];
		_ans701=辛;
		_ans702=乘單於雙(_ans700)(_ans701);
		_ans703=加單於雙(_ans699)(_ans702);

		壬=_ans703;
		_ans704=對數多項式乙上[1-1];
		_ans705=壬;
		_ans706=加單於雙(_ans704)(_ans705);
		_ans707=辛;
		_ans708=乘雙於雙(_ans706)(_ans707);
		_ans709=庚;
		_ans710=乘雙於雙(_ans708)(_ans709);
		_ans711=庚;
		_ans712=加雙於雙(_ans710)(_ans711);

		癸=_ans712;
		_ans713=癸[1-1];
		_ans714=_ans713*2;
		_ans715=二之對數上*位;
		_ans716=相加得雙(_ans714)(_ans715);

		子=_ans716;
		_ans717=癸[2-1];
		_ans718=_ans717*2;

		丑=_ans718;
		_ans719=子[2-1];
		_ans720=_ans719+丑;

		寅=_ans720;
		_ans721=二之對數下*位;
		_ans722=_ans721+寅;
		_ans723=子[1-1];
		_ans724=以小加大得雙(_ans722)(_ans723);

		底之對數=_ans724;
		""" "以下求冪之對數。" """
		_ans725=底之對數[1-1];
		_ans726=_ans725*指;

		卯=_ans726;

		if 卯>指數上溢限:
			_ans727=上溢(1);
			return _ans727

			if 卯<指數下溢限:
				_ans728=下溢(1);
				return _ans728

			_ans729=指;
			_ans730=底之對數;
			_ans731=乘單於雙(_ans729)(_ans730);

			冪之對數=_ans731;
			_ans732=冪之對數[1-1];
			_ans733=_ans732/二之對數;
			_ans734=取整(_ans733);

			移位數=_ans734;
			_ans735=移位數*二之對數下;
			_ans736=移位數*二之對數上;
			_ans737=以小加大得雙(_ans735)(_ans736);
			_ans738=雙數取反(_ans737);
			_ans739=冪之對數;
			_ans740=加雙於雙(_ans738)(_ans739);

			辰=_ans740;
			_ans741=辰[1-1];
			_ans742=指數(_ans741);
			_ans743=移位數;
			_ans744=浮點移位(_ans742)(_ans743);
			return _ans744
		return _rand29;
	return undefined;

""" "冪。同Javascript之Math.pow也。" """
冪=lambda _:0
def 冪 (底):
	def _rand30(指):
		nonlocal 底;
		global 進制;
		global 退制;
		global 總算位;
		global 上位冪;
		global 下位冪;
		global 至大指;
		global 巨位冪;
		global 至巨數;
		global 至小指;
		global 微位冪;
		global 至微數;
		global 位極差;
		global 浮點零;
		global 浮點一;
		global 試界;
		global 盤古;
		global 圓周率;
		global 倍圓周率;
		global 半圓周率;
		global 四分圓周率;
		global 自然常數;
		global 歐拉常數;
		global 黃金分割數;
		global 二之平方根;
		global 二之對數;
		global 十之對數;
		global 不可算數乎;
		global 下溢;
		global 上溢;
		global 除以零;
		global 不可算;
		global 求進冪;
		global 取位常數甲;
		global 取位常數乙;
		global 取位上溢限;
		global 分算常數;
		global 分算上溢限甲;
		global 分算上溢限乙;
		global 伏羲;
		global 取本位冪;
		global 取內鄰數;
		global 取外鄰數;
		global 分算;
		global 造雙數;
		global 雙數取反;
		global 以小加大得雙;
		global 相加得雙;
		global 加單於雙;
		global 以單減雙得單;
		global 加雙於雙;
		global 自乘得雙;
		global 相乘得雙;
		global 乘單於雙;
		global 雙數自乘;
		global 乘雙於雙;
		global 求多項式;
		global 浮點移位;
		global 析浮點數;
		global 取底除;
		global 取整除;
		global 半圓周率密率;
		global 分四象;
		global 正餘弦角限;
		global 正弦多項式;
		global 餘弦多項式;
		global 正弦;
		global 餘弦;
		global 反正弦多項式;
		global 反正弦;
		global 反餘弦;
		global 正切;
		global 反正切多項式;
		global 反正切;
		global 勾股求角;
		global 勾股求弦常數下;
		global 勾股求弦;
		global 二之對數下;
		global 對數多項式甲;
		global 對數;
		global 指數多項式甲;
		global 指數;
		global 對數多項式乙上;
		global 對數多項式乙下;
		global 正數之冪;
		global 冪;

		if 指==0:
			return 1

			if 指==1:
				return 底

				if 指==2:
					_ans745=底*底;
					return _ans745

					if 指==-1:
						_ans746=1/底;
						return _ans746

						if 指==0.5:
							_ans747=平方根(底);
							return _ans747

							if 指==3:
								_ans748=底*底;
								_ans749=底*_ans748;
								return _ans749

								if 指==-2:
									_ans750=1/底;
									_ans751=_ans750/底;
									return _ans751

									if 指==-0.5:
										_ans752=平方根(底);
										_ans753=1/_ans752;
										return _ans753


									if 底==1:
										return 1

									_ans754=不可算數乎(底);

									if _ans754:
										return 底

									_ans755=不可算數乎(指);

									if _ans755:
										return 指

									_ans756=絕對(底);

									甲=_ans756;
									_ans757=絕對(指);

									乙=_ans757;

									if 乙>至巨數:

										if 甲==1:
											return 1

											if 甲<1:

												if 指>0:
													return 浮點零

												else:
													return 乙


											else:

												if 指>0:
													return 乙

												else:
													return 浮點零



										指為偶數=False
										指為奇數=False
										指非整數=False
										_ans758=乙%2;

										丙=_ans758;

										if 丙==0:

											指為偶數=True;

											if 丙==1:

												指為奇數=True;

											else:

												指非整數=True;


											if 底==0:

												if 指<0:

													if 指為奇數:
														_ans759=1/底;
														return _ans759

													else:
														_ans760=1/甲;
														return _ans760


												else:

													if 指為奇數:
														return 底

													else:
														return 甲



												if 甲>至巨數:

													if 指<0:

														if 指為奇數:
															_ans761=正負(底);
															_ans762=浮點零*_ans761;
															return _ans762

														else:
															return 浮點零


													else:

														if 指為奇數:
															return 底

														else:
															return 甲



													if 底<0:

														if 指非整數:
															_ans763=不可算();
															return _ans763

															if 指為奇數:
																_ans764=正數之冪(甲)(指);
																_ans765=_ans764*-1;
																return _ans765


														_ans766=正數之冪(甲)(指);
														return _ans766
													return _rand30;
												return undefined;
											return undefined;
										return undefined;
									return undefined;
								return undefined;
							return undefined;
						return undefined;
					return undefined;
				return undefined;
			return undefined;
		return undefined;
	return undefined;

平方根常數甲=0.417319
""" " (2^0.5 - 1) * sqrt((2^0.25 + 2^-0.25) / 2) " """
_ans767=二之平方根-1;
_ans768=_ans767*2;

平方根常數乙=_ans768;
_ans769=微位冪*上位冪;
_ans770=_ans769*進制;
_ans771=_ans770*進制;

平方根下溢界=_ans771;
""" "平方根。同Javascript之Math.sqrt也。" """
平方根=lambda _:0
def 平方根 (甲):
	global 進制;
	global 退制;
	global 總算位;
	global 上位冪;
	global 下位冪;
	global 至大指;
	global 巨位冪;
	global 至巨數;
	global 至小指;
	global 微位冪;
	global 至微數;
	global 位極差;
	global 浮點零;
	global 浮點一;
	global 試界;
	global 盤古;
	global 圓周率;
	global 倍圓周率;
	global 半圓周率;
	global 四分圓周率;
	global 自然常數;
	global 歐拉常數;
	global 黃金分割數;
	global 二之平方根;
	global 二之對數;
	global 十之對數;
	global 不可算數乎;
	global 下溢;
	global 上溢;
	global 除以零;
	global 不可算;
	global 求進冪;
	global 取位常數甲;
	global 取位常數乙;
	global 取位上溢限;
	global 分算常數;
	global 分算上溢限甲;
	global 分算上溢限乙;
	global 伏羲;
	global 取本位冪;
	global 取內鄰數;
	global 取外鄰數;
	global 分算;
	global 造雙數;
	global 雙數取反;
	global 以小加大得雙;
	global 相加得雙;
	global 加單於雙;
	global 以單減雙得單;
	global 加雙於雙;
	global 自乘得雙;
	global 相乘得雙;
	global 乘單於雙;
	global 雙數自乘;
	global 乘雙於雙;
	global 求多項式;
	global 浮點移位;
	global 析浮點數;
	global 取底除;
	global 取整除;
	global 半圓周率密率;
	global 分四象;
	global 正餘弦角限;
	global 正弦多項式;
	global 餘弦多項式;
	global 正弦;
	global 餘弦;
	global 反正弦多項式;
	global 反正弦;
	global 反餘弦;
	global 正切;
	global 反正切多項式;
	global 反正切;
	global 勾股求角;
	global 勾股求弦常數下;
	global 勾股求弦;
	global 二之對數下;
	global 對數多項式甲;
	global 對數;
	global 指數多項式甲;
	global 指數;
	global 對數多項式乙上;
	global 對數多項式乙下;
	global 正數之冪;
	global 冪;
	global 平方根常數甲;
	global 平方根;
	非常=True

	if 甲>=平方根下溢界:

		if 甲<巨位冪:

			非常=False;



	if 非常:

		if 甲==0:
			return 浮點零

		_ans772=不可算數乎(甲);

		if _ans772:
			return 甲


		if 甲>至巨數:
			return 甲


		if 甲<0:
			_ans773=不可算();
			return _ans773


		if 甲<=平方根下溢界:
			_ans774=甲*上位冪;
			_ans775=_ans774*上位冪;
			_ans776=_ans775*進制;
			_ans777=_ans776*進制;
			_ans778=平方根(_ans777);
			_ans779=_ans778*下位冪;
			_ans780=_ans779*退制;
			return _ans780


		if 甲>=巨位冪:
			_ans781=甲*退制;
			_ans782=_ans781*退制;
			_ans783=平方根(_ans782);
			_ans784=_ans783*進制;
			return _ans784


	_ans785=析浮點數(甲);

	析甲=_ans785;
	_ans786=析甲["位"];
	_ans787=_ans786/2;

	半位=_ans787;
	_ans788=取底(半位);

	整半位=_ans788;
	_ans789=析甲["本"];
	_ans790=_ans789+二之平方根;
	_ans791=_ans790*平方根常數甲;

	丁=_ans791;
	_ans792=半位-整半位;
	_ans793=_ans792*平方根常數乙;
	_ans794=_ans793+1;
	_ans795=_ans794*丁;

	戊=_ans795;
	_ans796=求進冪(整半位);

	己=_ans796;
	_ans797=戊*己;

	乙=_ans797;
	""" "以上求疏根" """
	""" "蓋用牛頓法耳" """
	for _rand31 in range(3):
		_ans798=甲/乙;
		_ans799=_ans798+乙;
		_ans800=_ans799/2;

		丙=_ans800;

		乙=丙;

	""" "以下校末位。" """
	_ans801=己*下位冪;

	庚=_ans801;
	_ans802=乙-庚;

	下數=_ans802;
	_ans803=相乘得雙(乙)(下數);

	下積=_ans803;
	_ans804=下積[1-1];

	if _ans804>甲:
		return 下數

	_ans805=下積[1-1];

	if _ans805==甲:
		_ans806=下積[2-1];

		if _ans806>=0:
			return 下數


	""" "若甲等於中數乘下數者。其平方根不足下半間數。捨餘得下數也。" """
	_ans807=乙+庚;

	上數=_ans807;
	_ans808=相乘得雙(乙)(上數);

	上積=_ans808;
	_ans809=上積[1-1];

	if _ans809<甲:
		return 上數

	_ans810=上積[1-1];

	if _ans810==甲:
		_ans811=上積[2-1];

		if _ans811<0:
			return 上數


	""" "若甲等於中數乘上數者。其平方根不足上半間數。捨餘得中數也。" """
	return 乙

""" "絕對。同Javascript之Math.abs也。" """
絕對=lambda _:0
def 絕對 (甲):
	global 進制;
	global 退制;
	global 總算位;
	global 上位冪;
	global 下位冪;
	global 至大指;
	global 巨位冪;
	global 至巨數;
	global 至小指;
	global 微位冪;
	global 至微數;
	global 位極差;
	global 浮點零;
	global 浮點一;
	global 試界;
	global 盤古;
	global 圓周率;
	global 倍圓周率;
	global 半圓周率;
	global 四分圓周率;
	global 自然常數;
	global 歐拉常數;
	global 黃金分割數;
	global 二之平方根;
	global 二之對數;
	global 十之對數;
	global 不可算數乎;
	global 下溢;
	global 上溢;
	global 除以零;
	global 不可算;
	global 求進冪;
	global 取位常數甲;
	global 取位常數乙;
	global 取位上溢限;
	global 分算常數;
	global 分算上溢限甲;
	global 分算上溢限乙;
	global 伏羲;
	global 取本位冪;
	global 取內鄰數;
	global 取外鄰數;
	global 分算;
	global 造雙數;
	global 雙數取反;
	global 以小加大得雙;
	global 相加得雙;
	global 加單於雙;
	global 以單減雙得單;
	global 加雙於雙;
	global 自乘得雙;
	global 相乘得雙;
	global 乘單於雙;
	global 雙數自乘;
	global 乘雙於雙;
	global 求多項式;
	global 浮點移位;
	global 析浮點數;
	global 取底除;
	global 取整除;
	global 半圓周率密率;
	global 分四象;
	global 正餘弦角限;
	global 正弦多項式;
	global 餘弦多項式;
	global 正弦;
	global 餘弦;
	global 反正弦多項式;
	global 反正弦;
	global 反餘弦;
	global 正切;
	global 反正切多項式;
	global 反正切;
	global 勾股求角;
	global 勾股求弦常數下;
	global 勾股求弦;
	global 二之對數下;
	global 對數多項式甲;
	global 對數;
	global 指數多項式甲;
	global 指數;
	global 對數多項式乙上;
	global 對數多項式乙下;
	global 正數之冪;
	global 冪;
	global 平方根常數甲;
	global 平方根;
	global 絕對;
	_ans812=正負(甲);

	符=_ans812;
	_ans813=甲*符;
	return _ans813

""" "取頂。同Javascript之Math.ceil也。" """
取頂=lambda _:0
def 取頂 (甲):
	global 進制;
	global 退制;
	global 總算位;
	global 上位冪;
	global 下位冪;
	global 至大指;
	global 巨位冪;
	global 至巨數;
	global 至小指;
	global 微位冪;
	global 至微數;
	global 位極差;
	global 浮點零;
	global 浮點一;
	global 試界;
	global 盤古;
	global 圓周率;
	global 倍圓周率;
	global 半圓周率;
	global 四分圓周率;
	global 自然常數;
	global 歐拉常數;
	global 黃金分割數;
	global 二之平方根;
	global 二之對數;
	global 十之對數;
	global 不可算數乎;
	global 下溢;
	global 上溢;
	global 除以零;
	global 不可算;
	global 求進冪;
	global 取位常數甲;
	global 取位常數乙;
	global 取位上溢限;
	global 分算常數;
	global 分算上溢限甲;
	global 分算上溢限乙;
	global 伏羲;
	global 取本位冪;
	global 取內鄰數;
	global 取外鄰數;
	global 分算;
	global 造雙數;
	global 雙數取反;
	global 以小加大得雙;
	global 相加得雙;
	global 加單於雙;
	global 以單減雙得單;
	global 加雙於雙;
	global 自乘得雙;
	global 相乘得雙;
	global 乘單於雙;
	global 雙數自乘;
	global 乘雙於雙;
	global 求多項式;
	global 浮點移位;
	global 析浮點數;
	global 取底除;
	global 取整除;
	global 半圓周率密率;
	global 分四象;
	global 正餘弦角限;
	global 正弦多項式;
	global 餘弦多項式;
	global 正弦;
	global 餘弦;
	global 反正弦多項式;
	global 反正弦;
	global 反餘弦;
	global 正切;
	global 反正切多項式;
	global 反正切;
	global 勾股求角;
	global 勾股求弦常數下;
	global 勾股求弦;
	global 二之對數下;
	global 對數多項式甲;
	global 對數;
	global 指數多項式甲;
	global 指數;
	global 對數多項式乙上;
	global 對數多項式乙下;
	global 正數之冪;
	global 冪;
	global 平方根常數甲;
	global 平方根;
	global 絕對;
	global 取頂;
	_ans814=甲*-1;
	_ans815=取底(_ans814);
	_ans816=_ans815*-1;
	return _ans816

""" "取底。同Javascript之Math.floor也。" """
取底=lambda _:0
def 取底 (甲):
	global 進制;
	global 退制;
	global 總算位;
	global 上位冪;
	global 下位冪;
	global 至大指;
	global 巨位冪;
	global 至巨數;
	global 至小指;
	global 微位冪;
	global 至微數;
	global 位極差;
	global 浮點零;
	global 浮點一;
	global 試界;
	global 盤古;
	global 圓周率;
	global 倍圓周率;
	global 半圓周率;
	global 四分圓周率;
	global 自然常數;
	global 歐拉常數;
	global 黃金分割數;
	global 二之平方根;
	global 二之對數;
	global 十之對數;
	global 不可算數乎;
	global 下溢;
	global 上溢;
	global 除以零;
	global 不可算;
	global 求進冪;
	global 取位常數甲;
	global 取位常數乙;
	global 取位上溢限;
	global 分算常數;
	global 分算上溢限甲;
	global 分算上溢限乙;
	global 伏羲;
	global 取本位冪;
	global 取內鄰數;
	global 取外鄰數;
	global 分算;
	global 造雙數;
	global 雙數取反;
	global 以小加大得雙;
	global 相加得雙;
	global 加單於雙;
	global 以單減雙得單;
	global 加雙於雙;
	global 自乘得雙;
	global 相乘得雙;
	global 乘單於雙;
	global 雙數自乘;
	global 乘雙於雙;
	global 求多項式;
	global 浮點移位;
	global 析浮點數;
	global 取底除;
	global 取整除;
	global 半圓周率密率;
	global 分四象;
	global 正餘弦角限;
	global 正弦多項式;
	global 餘弦多項式;
	global 正弦;
	global 餘弦;
	global 反正弦多項式;
	global 反正弦;
	global 反餘弦;
	global 正切;
	global 反正切多項式;
	global 反正切;
	global 勾股求角;
	global 勾股求弦常數下;
	global 勾股求弦;
	global 二之對數下;
	global 對數多項式甲;
	global 對數;
	global 指數多項式甲;
	global 指數;
	global 對數多項式乙上;
	global 對數多項式乙下;
	global 正數之冪;
	global 冪;
	global 平方根常數甲;
	global 平方根;
	global 絕對;
	global 取頂;
	global 取底;
	_ans817=正負(甲);

	符=_ans817;
	_ans818=甲*符;

	乙=_ans818;
	""" "JavaScript者。除負以正。所餘負也。Python者。除負以正。所餘正也。" """
	_ans819=乙%1;

	丙=_ans819;

	if 丙>0:
		_ans820=乙-丙;
		_ans821=_ans820*符;

		丁=_ans821;

		if 符<0:
			_ans822=丁-1;
			return _ans822

		else:
			return 丁


	else:
		return 甲


""" "取整。同Javascript之Math.round, but rounded away from zero when the fractional part is exactly 0.5也。" """
取整=lambda _:0
def 取整 (甲):
	global 進制;
	global 退制;
	global 總算位;
	global 上位冪;
	global 下位冪;
	global 至大指;
	global 巨位冪;
	global 至巨數;
	global 至小指;
	global 微位冪;
	global 至微數;
	global 位極差;
	global 浮點零;
	global 浮點一;
	global 試界;
	global 盤古;
	global 圓周率;
	global 倍圓周率;
	global 半圓周率;
	global 四分圓周率;
	global 自然常數;
	global 歐拉常數;
	global 黃金分割數;
	global 二之平方根;
	global 二之對數;
	global 十之對數;
	global 不可算數乎;
	global 下溢;
	global 上溢;
	global 除以零;
	global 不可算;
	global 求進冪;
	global 取位常數甲;
	global 取位常數乙;
	global 取位上溢限;
	global 分算常數;
	global 分算上溢限甲;
	global 分算上溢限乙;
	global 伏羲;
	global 取本位冪;
	global 取內鄰數;
	global 取外鄰數;
	global 分算;
	global 造雙數;
	global 雙數取反;
	global 以小加大得雙;
	global 相加得雙;
	global 加單於雙;
	global 以單減雙得單;
	global 加雙於雙;
	global 自乘得雙;
	global 相乘得雙;
	global 乘單於雙;
	global 雙數自乘;
	global 乘雙於雙;
	global 求多項式;
	global 浮點移位;
	global 析浮點數;
	global 取底除;
	global 取整除;
	global 半圓周率密率;
	global 分四象;
	global 正餘弦角限;
	global 正弦多項式;
	global 餘弦多項式;
	global 正弦;
	global 餘弦;
	global 反正弦多項式;
	global 反正弦;
	global 反餘弦;
	global 正切;
	global 反正切多項式;
	global 反正切;
	global 勾股求角;
	global 勾股求弦常數下;
	global 勾股求弦;
	global 二之對數下;
	global 對數多項式甲;
	global 對數;
	global 指數多項式甲;
	global 指數;
	global 對數多項式乙上;
	global 對數多項式乙下;
	global 正數之冪;
	global 冪;
	global 平方根常數甲;
	global 平方根;
	global 絕對;
	global 取頂;
	global 取底;
	global 取整;
	_ans823=正負(甲);

	符=_ans823;
	_ans824=甲*符;

	乙=_ans824;
	_ans825=乙%1;

	丙=_ans825;

	if 丙==丙:

		if 丙<0.5:
			_ans826=乙-丙;
			_ans827=_ans826*符;
			return _ans827

		else:
			_ans828=乙-丙;
			_ans829=_ans828+1;
			_ans830=_ans829*符;
			return _ans830


	else:
		return 甲


""" "捨餘。同Javascript之Math.trunc也。" """
捨餘=lambda _:0
def 捨餘 (甲):
	global 進制;
	global 退制;
	global 總算位;
	global 上位冪;
	global 下位冪;
	global 至大指;
	global 巨位冪;
	global 至巨數;
	global 至小指;
	global 微位冪;
	global 至微數;
	global 位極差;
	global 浮點零;
	global 浮點一;
	global 試界;
	global 盤古;
	global 圓周率;
	global 倍圓周率;
	global 半圓周率;
	global 四分圓周率;
	global 自然常數;
	global 歐拉常數;
	global 黃金分割數;
	global 二之平方根;
	global 二之對數;
	global 十之對數;
	global 不可算數乎;
	global 下溢;
	global 上溢;
	global 除以零;
	global 不可算;
	global 求進冪;
	global 取位常數甲;
	global 取位常數乙;
	global 取位上溢限;
	global 分算常數;
	global 分算上溢限甲;
	global 分算上溢限乙;
	global 伏羲;
	global 取本位冪;
	global 取內鄰數;
	global 取外鄰數;
	global 分算;
	global 造雙數;
	global 雙數取反;
	global 以小加大得雙;
	global 相加得雙;
	global 加單於雙;
	global 以單減雙得單;
	global 加雙於雙;
	global 自乘得雙;
	global 相乘得雙;
	global 乘單於雙;
	global 雙數自乘;
	global 乘雙於雙;
	global 求多項式;
	global 浮點移位;
	global 析浮點數;
	global 取底除;
	global 取整除;
	global 半圓周率密率;
	global 分四象;
	global 正餘弦角限;
	global 正弦多項式;
	global 餘弦多項式;
	global 正弦;
	global 餘弦;
	global 反正弦多項式;
	global 反正弦;
	global 反餘弦;
	global 正切;
	global 反正切多項式;
	global 反正切;
	global 勾股求角;
	global 勾股求弦常數下;
	global 勾股求弦;
	global 二之對數下;
	global 對數多項式甲;
	global 對數;
	global 指數多項式甲;
	global 指數;
	global 對數多項式乙上;
	global 對數多項式乙下;
	global 正數之冪;
	global 冪;
	global 平方根常數甲;
	global 平方根;
	global 絕對;
	global 取頂;
	global 取底;
	global 取整;
	global 捨餘;
	_ans831=正負(甲);

	符=_ans831;
	_ans832=甲*符;

	乙=_ans832;
	_ans833=乙%1;

	丙=_ans833;

	if 丙==丙:
		_ans834=乙-丙;
		_ans835=_ans834*符;
		return _ans835

	else:
		return 甲


""" "正負。同Javascript之Math.sign也。" """
正負=lambda _:0
def 正負 (甲):
	global 進制;
	global 退制;
	global 總算位;
	global 上位冪;
	global 下位冪;
	global 至大指;
	global 巨位冪;
	global 至巨數;
	global 至小指;
	global 微位冪;
	global 至微數;
	global 位極差;
	global 浮點零;
	global 浮點一;
	global 試界;
	global 盤古;
	global 圓周率;
	global 倍圓周率;
	global 半圓周率;
	global 四分圓周率;
	global 自然常數;
	global 歐拉常數;
	global 黃金分割數;
	global 二之平方根;
	global 二之對數;
	global 十之對數;
	global 不可算數乎;
	global 下溢;
	global 上溢;
	global 除以零;
	global 不可算;
	global 求進冪;
	global 取位常數甲;
	global 取位常數乙;
	global 取位上溢限;
	global 分算常數;
	global 分算上溢限甲;
	global 分算上溢限乙;
	global 伏羲;
	global 取本位冪;
	global 取內鄰數;
	global 取外鄰數;
	global 分算;
	global 造雙數;
	global 雙數取反;
	global 以小加大得雙;
	global 相加得雙;
	global 加單於雙;
	global 以單減雙得單;
	global 加雙於雙;
	global 自乘得雙;
	global 相乘得雙;
	global 乘單於雙;
	global 雙數自乘;
	global 乘雙於雙;
	global 求多項式;
	global 浮點移位;
	global 析浮點數;
	global 取底除;
	global 取整除;
	global 半圓周率密率;
	global 分四象;
	global 正餘弦角限;
	global 正弦多項式;
	global 餘弦多項式;
	global 正弦;
	global 餘弦;
	global 反正弦多項式;
	global 反正弦;
	global 反餘弦;
	global 正切;
	global 反正切多項式;
	global 反正切;
	global 勾股求角;
	global 勾股求弦常數下;
	global 勾股求弦;
	global 二之對數下;
	global 對數多項式甲;
	global 對數;
	global 指數多項式甲;
	global 指數;
	global 對數多項式乙上;
	global 對數多項式乙下;
	global 正數之冪;
	global 冪;
	global 平方根常數甲;
	global 平方根;
	global 絕對;
	global 取頂;
	global 取底;
	global 取整;
	global 捨餘;
	global 正負;

	if 甲>0:
		return 1


	if 甲<0:
		return -1

	return 甲


#/*___wenyan_module_算經_end___*/
# -*- coding: utf-8 -*-
class Ctnr:
  def __init__(self):self.dict = dict();self.length = 0;self.it = -1;
  def push(self,*args):
    for arg in args:
      self.dict[str(self.length)]=arg; self.length+=1
  def __getitem__(self,i):
    try: return self.dict[str(i)]
    except: return None
  def __setitem__(self,i,x):
    self.dict[str(i)]=x
    inti = None
    try:
      inti = int(i)
      if (abs(inti - float(i))>0.0001): inti=None
    except: pass
    if (inti != None):
      self.length=inti+1
      for j in range(0,self.length):
        try:  self.dict[str(j)]
        except: self.dict[str(j)]=None
  def slice(self,i):
    ret = Ctnr();
    for i in range(i,self.length): ret.push(self[i])
    return ret
  def concat(self,other):
    ret = Ctnr();
    for i in range(0,self.length): ret.push(self[i])
    for i in range(0,other.length): ret.push(other[i])
    return ret
  def __str__(self):
    if (len(self.dict.keys())==self.length):
      ret = "["
      for k in range(0,self.length):
        v = self[k]
        if (isinstance(v,Ctnr)): ret += v.__str__()
        else: ret += str(v)
        ret+=","
      ret += "]"
      return ret;
    else:
      ret = "{"
      for k in self.dict.keys():
        ret += str(k)+":"
        v = self.dict[k]
        if (isinstance(v,Ctnr)): ret += v.__str__()
        else: ret += str(v)
        ret+=","
      ret += "}"
      return ret;
  def __repr__(self):
    return self.__str__()
  def __iter__(self):
    self.it = -1;
    return self
  def __next__(self):
    self.it += 1
    if (self.it >= self.length): raise StopIteration()
    return self[self.it]
globals()['Ctnr']=Ctnr;
class JSON:
  @staticmethod
  def stringify(x):
    return x;
#####
""" "死帶框架 — Deadband Constrained Framework\n以文言述之，合於華夏哲理。\n天行有常，陰陽相推，殼層自明。\nHexagonal lattice meets I Ching. Constraint theory meets 中庸。" """
正弦=正弦;餘弦=餘弦;平方根=平方根;取整=取整;取底=取底;取頂=取頂;絕對=絕對;正負=正負;圓周率=圓周率;黃金分割數=黃金分割數;占=占;運=運;""" "常數之部 — Constants of Heaven and Earth" """
一=1
二=2
三=3
六=6
_ans1=0

零點五=0;
""" "sqrt(3) — 三之根號，天地之度" """
_ans2=平方根(三);

三根=_ans2;
""" "360 — 周天之數，三百六十度，天行一周" """
周天=360
""" "2*pi/3 — 百二十度，三方之角" """
_ans3=二*圓周率;
_ans4=_ans3/三;

三方角=_ans4;
""" "=======================================================\n第一術：周天之數 — Modulo 360 Arithmetic\n天行有常，周而復始。\n三百六十度者，二十四節氣之十五度也。\n360 = 24 solar terms x 15 degrees — Heaven's own periodicity.\n=======================================================" """
周天加=lambda _:0
def 周天加 (甲):
	def _rand1(乙):
		nonlocal 甲;
		global 一;
		global 二;
		global 三;
		global 六;
		global 周天;
		global 周天加;
		""" "天行加法：兩數相加，取周天之餘" """
		_ans5=甲+乙;

		和=_ans5;
		_ans6=和%周天;

		餘=_ans6;

		if 餘>=0:
			return 餘

		else:
			_ans7=餘+周天;

			正餘=_ans7;
			return 正餘

	return _rand1;

周天減=lambda _:0
def 周天減 (甲):
	def _rand2(乙):
		nonlocal 甲;
		global 一;
		global 二;
		global 三;
		global 六;
		global 周天;
		global 周天加;
		global 周天減;
		""" "天行減法：周而復始，無有窮盡" """
		_ans8=甲-乙;

		差=_ans8;
		_ans9=差%周天;

		餘=_ans9;

		if 餘>=0:
			return 餘

		else:
			_ans10=餘+周天;

			正餘=_ans10;
			return 正餘

	return _rand2;

""" "=======================================================\n第二術：艾氏格點 — Eisenstein Integer Snap\n近取諸身，遠取諸物。\nThe hexagonal lattice reveals the nearest truth.\n=======================================================" """
艾氏格點=lambda _:0
def 艾氏格點 (實):
	def _rand3(虛):
		nonlocal 實;
		global 一;
		global 二;
		global 三;
		global 六;
		global 周天;
		global 周天加;
		global 周天減;
		global 艾氏格點;
		""" "取最近艾森斯坦整數。龜甲之上，尋其最近之格。" """
		""" "b = round(2*Im / sqrt(3))" """
		_ans11=二*虛;

		二虛=_ans11;
		_ans12=二虛/三根;

		乙比=_ans12;
		_ans13=取整(乙比);

		乙整=_ans13;
		""" "a = round(Re - b/2)" """
		_ans14=乙整/二;

		半乙=_ans14;
		_ans15=實-半乙;

		甲減半=_ans15;
		_ans16=取整(甲減半);

		甲整=_ans16;
		""" "返回物 {a: 甲整, b: 乙整}" """
		_ans17={}
		_ans17={"甲":0,"乙":0,};

		格點["甲"]=甲整;

		格點["乙"]=乙整;
		return 格點
	return _rand3;

""" "=======================================================\n第三術：六角分布 — Hexagonal PDF Sampling\n隨機取樣，合於六角之形。\n=======================================================" """
六角分布=lambda _:0
def 六角分布 (種):
	global 一;
	global 二;
	global 三;
	global 六;
	global 周天;
	global 周天加;
	global 周天減;
	global 艾氏格點;
	global 六角分布;
	""" "以易經之占法，取六角形中之隨機點" """
	_ans18=運(種);
	while (True):
		_ans19=占();

		隨甲=_ans19;
		_ans20=占();

		隨乙=_ans20;
		""" "Map to [-1, 1]" """
		_ans21=隨甲-零點五;

		甲減=_ans21;
		_ans22=甲減*二;

		甲二=_ans22;
		_ans23=隨乙-零點五;

		乙減=_ans23;
		_ans24=乙減*二;

		乙二=_ans24;
		""" "Check hexagonal boundary" """
		_ans25=絕對(甲二);

		甲絕=_ans25;
		_ans26=一-甲絕;

		一減甲=_ans26;
		_ans27=一減甲*三根;

		限=_ans27;
		_ans28=絕對(乙二);

		乙絕=_ans28;

		if 乙絕<=限:
			_ans29={}
			_ans29={"甲":0,"乙":0,};

			六角點["甲"]=甲二;

			六角點["乙"]=乙二;
			return 六角點



""" "=======================================================\n第四術：伯氏算法 — BMA Pattern Detection\n觀其象而察其序。\n=======================================================" """
伯氏算法=lambda _:0
def 伯氏算法 (列長):
	def _rand4(階):
		nonlocal 列長;
		global 一;
		global 二;
		global 三;
		global 六;
		global 周天;
		global 周天加;
		global 周天減;
		global 艾氏格點;
		global 六角分布;
		global 伯氏算法;
		""" "觀象察序：以二倍之階數觀測，揭示隱藏之序" """
		_ans30=二*階;

		二階=_ans30;
		""" "符號序列 — Build sign sequence from observation list" """
		符號列=Ctnr()
		計=0
		while (True):

			if 計>=二階:
				break

			""" "模擬觀測值：正數為陽，負數為陰" """
			_ans31=占();
			_ans32=_ans31*二;
			_ans33=_ans32-一;

			觀=_ans33;

			if 觀>0:
				符號列.push(True)

			else:
				符號列.push(False)

			_ans34=計+一;

			計=_ans34;

		""" "計算游程 — Count runs in sign sequence" """
		游程=0
		前計=1
		while (True):

			if 前計>=二階:
				break

			_ans35=前計-一;

			前減一=_ans35;
			_ans36=符號列[前減一-1];

			前符=_ans36;
			_ans37=符號列[前計-1];

			後符=_ans37;

			if 前符!=後符:
				_ans38=游程+一;

				游程=_ans38;

			_ans39=前計+一;

			前計=_ans39;

		""" "BMA detection: if runs < expected → pattern detected" """
		_ans40=二階*零點五;

		期望游程=_ans40;
		_ans41={}
		_ans41={"游程":0,"期望":0,"有序":false,};

		伯氏果["游程"]=游程;

		伯氏果["期望"]=期望游程;

		if 游程<=期望游程:

			伯氏果["有序"]=True;

		return 伯氏果
	return _rand4;

""" "=======================================================\n第五術：殼層分解 — Shell Decomposition\n陰陽相推，殼層自明。\n=======================================================" """
殼層分解=lambda _:0
def 殼層分解 (能):
	def _rand5(已知比):
		nonlocal 能;
		global 一;
		global 二;
		global 三;
		global 六;
		global 周天;
		global 周天加;
		global 周天減;
		global 艾氏格點;
		global 六角分布;
		global 伯氏算法;
		global 殼層分解;
		""" "已知者陽也，未知者陰也，邊界者道也" """
		_ans42=能*已知比;

		已知能=_ans42;
		_ans43=能-已知能;

		未知能=_ans43;
		""" "邊界 = sqrt(known * unknown) = the Dao between Yin and Yang" """
		_ans44=已知能*未知能;

		積=_ans44;
		_ans45=平方根(積);

		邊界=_ans45;
		_ans46={}
		_ans46={"已知":0,"未知":0,"邊界":0,"總能":0,};

		殼層["已知"]=已知能;

		殼層["未知"]=未知能;

		殼層["邊界"]=邊界;

		殼層["總能"]=能;
		return 殼層
	return _rand5;

""" "=======================================================\n第六術：感知門限 — Deadband Perceptibility Check\n知其白，守其黑。\n=======================================================" """
感知門限=lambda _:0
def 感知門限 (階):
	def _rand6(位數):
		nonlocal 階;
		global 一;
		global 二;
		global 三;
		global 六;
		global 周天;
		global 周天加;
		global 周天減;
		global 艾氏格點;
		global 六角分布;
		global 伯氏算法;
		global 殼層分解;
		global 感知門限;
		""" "以位數度之，能否感知階數之序？" """
		""" "Compute 2^k via repeated doubling" """
		二之幂=1
		幂計=0
		while (True):

			if 幂計>=位數:
				break

			_ans47=二之幂*二;

			二之幂=_ans47;
			_ans48=幂計+一;

			幂計=_ans48;

		""" "Minimum discriminable level = 360 / 2^k" """
		_ans49=周天/二之幂;

		門限=_ans49;
		""" "Required precision for order L = 360 / (L * 6)" """
		_ans50=階*六;

		階乘六=_ans50;
		_ans51=周天/階乘六;

		精度=_ans51;
		_ans52={}
		_ans52={"門限":0,"精度":0,"可感":false,};

		感知["門限"]=門限;

		感知["精度"]=精度;

		if 門限<=精度:

			感知["可感"]=True;

		return 感知
	return _rand6;

""" "=======================================================\n試驗之部 — Tests run via deadband-test.js\n驗之以數，明之以理。\n=======================================================" """
