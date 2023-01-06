import os
from lxml import etree
from io import BytesIO

#root = etree.XML("<root><a x='123'>aText<b/><c/><b/></a></root>")
#print(root.tag)
#print(etree.tostring(root))
#print(root.find("a").tag)
#print(root.findtext("a"))

schema_root = etree.XML('''\
           <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xs="http://www.w3.org/2001/XMLSchema">
            <xs:import namespace="http://schemas.xmlsoap.org/soap/envelope/" schemaLocation="http://schemas.xmlsoap.org/soap/envelope/"/>
            <xsd:element name="a" type="xsd:integer"/>
            <xsd:element name="b" type="xsd:integer"/>
            </xsd:schema>
            ''')
schema_root = etree.XML('''\
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
           xmlns:tns="http://schemas.xmlsoap.org/soap/envelope/"
           targetNamespace="http://schemas.xmlsoap.org/soap/envelope/" >

     
  <!-- Envelope, header and body -->
  <xs:element name="Envelope" type="tns:Envelope" />
  <xs:complexType name="Envelope" >
    <xs:sequence>
      <xs:element ref="tns:Header" minOccurs="0" />
      <xs:element ref="tns:Body" minOccurs="1" />
      <xs:any namespace="##other" minOccurs="0" maxOccurs="unbounded" processContents="lax" />
    </xs:sequence>
    <xs:anyAttribute namespace="##other" processContents="lax" />
  </xs:complexType>

  <xs:element name="Header" type="tns:Header" />
  <xs:complexType name="Header" >
    <xs:sequence>
      <xs:any namespace="##other" minOccurs="0" maxOccurs="unbounded" processContents="lax" />
    </xs:sequence>
    <xs:anyAttribute namespace="##other" processContents="lax" />
  </xs:complexType>
  
  <xs:element name="Body" type="tns:Body" />
  <xs:complexType name="Body" >
    <xs:sequence>
      <xs:any namespace="##any" minOccurs="0" maxOccurs="unbounded" processContents="lax" />
    </xs:sequence>
    <xs:anyAttribute namespace="##any" processContents="lax" >
	  <xs:annotation>
	    <xs:documentation>
		  Prose in the spec does not specify that attributes are allowed on the Body element
		</xs:documentation>
	  </xs:annotation>
	</xs:anyAttribute>
  </xs:complexType>

       
  <!-- Global Attributes.  The following attributes are intended to be usable via qualified attribute names on any complex type referencing them.  -->
  <xs:attribute name="mustUnderstand" >	
     <xs:simpleType>
     <xs:restriction base='xs:boolean'>
	   <xs:pattern value='0|1' />
	 </xs:restriction>
   </xs:simpleType>
  </xs:attribute>
  <xs:attribute name="actor" type="xs:anyURI" />

  <xs:simpleType name="encodingStyle" >
    <xs:annotation>
	  <xs:documentation>
	    'encodingStyle' indicates any canonicalization conventions followed in the contents of the containing element.  For example, the value 'http://schemas.xmlsoap.org/soap/encoding/' indicates the pattern described in SOAP specification
	  </xs:documentation>
	</xs:annotation>
    <xs:list itemType="xs:anyURI" />
  </xs:simpleType>

  <xs:attribute name="encodingStyle" type="tns:encodingStyle" />
  <xs:attributeGroup name="encodingStyle" >
    <xs:attribute ref="tns:encodingStyle" />
  </xs:attributeGroup>

  <xs:element name="Fault" type="tns:Fault" />
  <xs:complexType name="Fault" final="extension" >
    <xs:annotation>
	  <xs:documentation>
	    Fault reporting structure
	  </xs:documentation>
	</xs:annotation>
    <xs:sequence>
      <xs:element name="faultcode" type="xs:QName" />
      <xs:element name="faultstring" type="xs:string" />
      <xs:element name="faultactor" type="xs:anyURI" minOccurs="0" />
      <xs:element name="detail" type="tns:detail" minOccurs="0" />      
    </xs:sequence>
  </xs:complexType>

  <xs:complexType name="detail">
    <xs:sequence>
      <xs:any namespace="##any" minOccurs="0" maxOccurs="unbounded" processContents="lax" />
    </xs:sequence>
    <xs:anyAttribute namespace="##any" processContents="lax" /> 
  </xs:complexType>

</xs:schema>
''')
schema_root_etree = etree.XMLSchema(schema_root)
parser_root = etree.XMLParser(schema = schema_root_etree)


schema_api = etree.XML('''\
<xs:schema attributeFormDefault="unqualified" elementFormDefault="qualified" targetNamespace="http://tempuri.org/" xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="Add" type="tem:AddType" xmlns:tem="http://tempuri.org/"/>
  <xs:complexType name="AddType">
    <xs:sequence>
      <xs:element type="xs:integer" name="a" minOccurs="1"/>
      <xs:element type="xs:integer" name="b" maxOccurs="2"/>
    </xs:sequence>
  </xs:complexType>
</xs:schema>
''')
schema_api_etree = etree.XMLSchema(schema_api)
parser_api = etree.XMLParser(schema = schema_api_etree)


soapEnvelope = BytesIO(b'''<?xml version='1.0' encoding=\"utf-8\"?>
<soap:Envelope xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xmlns:xsd=\"http://www.w3.org/2001/XMLSchema\" xmlns:soap=\"http://schemas.xmlsoap.org/soap/envelope/\">
  <soap:Body>
    <Add xmlns=\"http://tempuri.org/\">
      <a>5</a>
      <b>11</b>
      <b>12</b>
    </Add>
  </soap:Body>
</soap:Envelope>
''')
try:
  treeSOAP = etree.parse(soapEnvelope, parser_root)
except Exception as ex:
  msgError = "{}".format(ex)
  print("XSD validation failed: ", msgError)
  quit()

rootSOAP = treeSOAP.getroot()

bodySOAPContent = rootSOAP.getchildren()[0].getchildren()[0]
#print("bodySOAPContent=", etree.tostring(bodySOAPContent))
try:
  tree = etree.parse(BytesIO(etree.tostring(bodySOAPContent, pretty_print=True)), parser_api)
except Exception as ex:
  msgError = "{}".format(ex)
  print("XSD validation failed: ", msgError)
  quit()

#print(rootSOAP.getchildren()[0].getchildren()[0].getchildren()[0].text)
#rootSOAP.getchildren()[0].getchildren()[0].getchildren()[0].text = "6"
#print(rootSOAP.getchildren()[0].getchildren()[0].getchildren()[0].text)

#print(rootSOAP.getchildren()[0].getchildren()[0].getchildren()[0].tag)
#rootSOAP.getchildren()[0].getchildren()[0].getchildren()[0].tag = "abcdef"
#print(rootSOAP.getchildren()[0].getchildren()[0].getchildren()[0].tag)
#print(etree.tostring(rootSOAP))

#root = etree.XML("<root><a x='123'>Jerome<b/><c/><b/></a></root>")
myXML = '''
<root>
  <a x='123'>Jerome
    <b/>
      <c/>
    <b/>
  </a>
</root>
'''
root = etree.XML(myXML)
print(root.find("a").tag)
print(root.find("a").text)

print(etree.tostring(rootSOAP))
print(rootSOAP.getchildren()[0].getchildren()[0].getchildren()[0].tag)
print(rootSOAP.find(".//{http://tempuri.org/}b").tag)

print(next(rootSOAP.iterfind(".//{http://tempuri.org/}b")).text)
mychild = next(rootSOAP.iterfind(".//{http://tempuri.org/}b"))
print(mychild.text)

print(rootSOAP.findall(".//{http://tempuri.org/}b")[1].text)
rootSOAP.findall(".//{http://tempuri.org/}b")[1].text = "14"
print(rootSOAP.findall(".//{http://tempuri.org/}b")[1].text)
print(etree.tostring(rootSOAP))
print(len(rootSOAP.findall(".//{http://tempuri.org/}b")))

text = "xpath1, xpath2,xpath3"
value = "value1,value2,value3"
list_1 = text.split(",")
list_value = value.split(",")
i = 0
for st in list_1:
  print(st.strip())
  print(list_value[i])
  i+=1