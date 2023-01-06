#!/usr/bin/env python3
import os
import kong_pdk.pdk.kong as kong
from lxml import etree
from io import BytesIO

import sys
sys.path.append("/usr/local/kong/python/lib")

import xsdSoapDefinition

Schema = (
    { "XPathReplace": {"type": "string", "required": False} },
    { "XPathReplaceAll": {"type": "boolean", "required": False} },
    { "XPathReplaceValue": {"type": "string", "required": False} },
    { "xsdApiSchema": {"type": "string", "required": False} },
    { "xsdSoapSchema": {"type": "string", "default": xsdSoapDefinition.XSD_SCHEMA_SOAP, "required": False} },
    { "xsltTransform": {"type": "string", "required": False} },
)

version = '1.1.0'
priority = 10

class XMLHandlingRequest:
    def __init__(self, config):
        self.config = config

    #-------------------------------------
    # Return a SOAP Fault to the Consumer
    #-------------------------------------
    def ReturnSOAPFault(self, kong, ErrMsg, ErrEx):
        msgError = """<?xml version="1.0" encoding="utf-8"?>
        <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
        <soap:Body>
            <soap:Fault>
                <faultcode>soap:Client</faultcode>
                    <faultstring>{}: {}</faultstring>
                    <detail/>
            </soap:Fault>
        </soap:Body>
        </soap:Envelope>""".format(ErrMsg, ErrEx)
        dictType = {"Content-Type": "text/xml; charset=utf-8"}
        # Don't call the backend API and send back to Consumer a SOAP Error Message
        return kong.response.exit(500, msgError, dictType)
        
    #-------------------------------------
    # Transform the XML content with XSLT
    #-------------------------------------
    def XSLTransform (self, kong):
        kong.log.notice("XSLTransform *** BEGIN ***")
        XSLTReplace = ""
        try:
            if 'xsltTransform' in self.config:
                XslTransform = self.config['xsltTransform']
        except:
            return

        # If there is no XSLT configuration we do nothing
        if XslTransform == "":
            kong.log.notice("No XSLT transformation is configured, so there is nothing to do")
            return

        # Get XML SOAP envelope from consumer's Request
        soapEnvelope = ""
        try:
            soapEnvelope = kong.request.get_raw_body()
        except Exception as ex:
            kong.log.err("Unable to get raw body from request, exception={}".format(ex))
            # Return a SOAP Fault to the Consumer
            self.ReturnSOAPFault(kong, "XSLT Transformation failed", ex)
            
        kong.log.notice("BEFORE XSLT transform, body= ", soapEnvelope)
        try:
            
            # Construct the XSLT transformer
            xslt_root = etree.XML(XslTransform)
            transform = etree.XSLT(xslt_root)

            # Run the transformation on the XML SOAP envelope
            doc = etree.parse(BytesIO(soapEnvelope))
            result_tree = transform(doc)
            
            # Remove empty Namepace added by the 'lxml' library (xmlns="")
            result_tree_no_empty_xmlns = etree.tostring(result_tree).replace(b' xmlns=""', b'')
            
            # Change the Consumer request with the new XST transformed values
            kong.log.notice("AFTER XSLT transform, body=", result_tree_no_empty_xmlns)
            kong.service.request.set_raw_body (result_tree_no_empty_xmlns)

        except Exception as ex:
            kong.log.err("XSLT Transformation, exception={}".format(ex))
            # Return a SOAP Fault to the Consumer
            self.ReturnSOAPFault(kong, "XSLT Transformation failed", ex)
        
        kong.log.notice("XSLTransform *** END ***")
    
    #---------------------------------
    # Replace the value of XPath tags
    #---------------------------------
    def XPathReplace (self, kong):
        kong.log.notice("XPathReplace *** BEGIN ***")

        # Get XPath to be replaced and Value
        XPathReplace = ""
        XPathReplaceAll = False
        XPathReplaceValue = ""
        try:
            if 'XPathReplace' in self.config:
                XPathReplace = self.config['XPathReplace']
            if 'XPathReplaceAll' in self.config:
                XPathReplaceAll = self.config['XPathReplaceAll']
            if 'XPathReplaceValue' in self.config:
                XPathReplaceValue = self.config['XPathReplaceValue']
        except:
            return
        
        kong.log.notice("XPathReplace={} | XPathReplaceAll={} | XPathReplaceValue={}".format(XPathReplace, XPathReplaceAll, XPathReplaceValue))
        
        # If there is no replacement, we exit
        if XPathReplace == "" or XPathReplaceValue == "":
            kong.log.notice("No XPATH replacement is configured, so there is nothing to do")
            return
        
        # If we don't have the same number of parameters of 'XPathReplace' and 'XPathReplaceValue' we return an Error
        if len(XPathReplace.split(",")) != len(XPathReplaceValue.split(",")):
            msgError = "The number of entries in 'XPathReplace' and 'XPathReplaceValue' are different"
            kong.log.err(msgError)
            # Return a SOAP Fault to the Consumer
            self.ReturnSOAPFault(kong, "XPath replacement failed", msgError)
            
        soapEnvelope = ""
        try:
            soapEnvelope = kong.request.get_raw_body()
        except Exception as ex:
            kong.log.err("Unable to get raw body from request, exception={}".format(ex))
            # Return a SOAP Fault to the Consumer
            self.ReturnSOAPFault(kong, "XPath replacement failed", ex)
        
        kong.log.notice("BEFORE XPath replacement, body= ", soapEnvelope)
        
        try:
            treeSOAP = etree.parse(BytesIO(soapEnvelope))
            rootSOAP = treeSOAP.getroot()
            # Create a list of all XPath entries and values to be replaced
            XPathReplace_list      = XPathReplace.split(",")
            XPathReplaceValue_list = XPathReplaceValue.split(",")
            v = 0

            # Iterate on each XPath entry to be replaced
            for XPathReplace_nth in XPathReplace_list:
                # Get matched number of XPath entries
                xpathNb = len(rootSOAP.findall(XPathReplace_nth.strip()))

                # If all XPath matched entries are replaced
                if XPathReplaceAll == True:
                    # Replace all XPath entries
                    for i in range(xpathNb):
                        rootSOAP.findall(XPathReplace_nth.strip())[i].text = XPathReplaceValue_list[v].strip()
                # Only 1st XPath match is replaced
                else:
                    rootSOAP.find(XPathReplace_nth.strip()).text = XPathReplaceValue_list[v].strip()
                # Increment the index for the Values list
                v += 1
            # Change the Consumer request with the new XPath values
            kong.service.request.set_raw_body (etree.tostring(rootSOAP))
            kong.log.notice("AFTER XPath replacement, body=", etree.tostring(rootSOAP))

        except Exception as ex:
            kong.log.err("Replace the value of XPath tags, exception={}".format(ex))
            msgError = "{}".format(ex)
            # Return a SOAP Fault to the Consumer
            self.ReturnSOAPFault(kong, "XPath replacement failed", ex)
        
        kong.log.notice("XPathReplace *** END ***")

    #--------------------------------------------------------------------
    # Validate XML against XSD schema
    # SOAP schema and API schema are defined in the configuration plugin
    #--------------------------------------------------------------------
    def XMLValidate (self, kong):
        kong.log.notice("XMLValidate *** BEGIN ***")
        soapEnvelope = ""
        tree = ""
        
        try:
            soapEnvelope = kong.request.get_raw_body()
        except Exception as ex:
            kong.log.err("Unable to get raw body from request, exception=", "%s" % (ex))
            return
        
        kong.log.notice("XMLValidate body= ", soapEnvelope)
        
        # Get XSD SOAP shema from the plugin configuration
        xsdSoapSchema = ""
        try:
            if 'xsdSoapSchema' in self.config:
                xsdSoapSchema = self.config['xsdSoapSchema']
        except:
            pass
        
        # If we have a Body content, we check the validity of SOAP envelope against its XSD schema
        if soapEnvelope != "" and xsdSoapSchema != "":
            try:
                kong.log.notice("Check SOAP Envelope XML against its XSD schema")

                # Load the SOAP envelope XSD schema
                schema_root_soap = etree.XML (xsdSoapSchema)
                schema_root_soap_etree = etree.XMLSchema(schema_root_soap)
                parse_root_soap = etree.XMLParser(schema = schema_root_soap_etree)
                
                # Parse the SOAP envelope (retrieved from request) against the schema
                tree = etree.parse(BytesIO(soapEnvelope), parse_root_soap)
            except Exception as ex:
                kong.log.err("Unable check the validity of SOAP envelope against its XSD schema, exception=", "%s" % (ex))
                # Return a SOAP Fault to the Consumer
                self.ReturnSOAPFault(kong, "XSD validation failed", ex)
    
        # Get XSD API shema from the plugin configuration
        xsdApiSchema = ""
        try:
            if 'xsdApiSchema' in self.config:
                xsdApiSchema = self.config['xsdApiSchema']
        except:
            pass

        # If we have a Body content, we check the validity of <soap:Body> content against its XSD schema
        if soapEnvelope != "" and xsdApiSchema != "":
            try:
                kong.log.notice("Check API XML against its XSD schema")
                if tree == "":
                    tree = etree.parse(BytesIO(soapEnvelope))

                # Load the API XSD schema
                schema_api = etree.XML(xsdApiSchema)
                schema_api_etree = etree.XMLSchema(schema_api)
                parser_api = etree.XMLParser(schema = schema_api_etree)

                # Get <soap:Body> content from entire <soap:Envelope>
                #
                # Example:
                # <soap:Envelope xmlns:xsi=....">
                #   <soap:Body>
                #     <Add xmlns="http://tempuri.org/">
                #       <a>5</a>
                #       <b>7</b>
                #     </Add>
                #   </soap:Body>
                # </soap:Envelope>
                root = tree.getroot()

                # root.getchildren()[0] => <soap:Body>...</soap:Body>
                # root.getchildren()[0].getchildren()[0] => <Add ...</Add>
                bodySOAPContent = root.getchildren()[0].getchildren()[0]
                kong.log.notice("etree.tostring(bodySOAPContent=", etree.tostring(bodySOAPContent))
                
                # Parse the SOAP envelope (retrieved from request) agains the schema
                tree = etree.parse(BytesIO(etree.tostring(bodySOAPContent)), parser_api)
            except Exception as ex:
                kong.log.err("Unable check the validity of API content against its XSD schema, exception=", "%s" % (ex))
                # Return a SOAP Fault to the Consumer
                self.ReturnSOAPFault(kong, "XSD validation failed", ex)

        kong.log.notice("XMLValidate *** END ***")

#--------------------------------------------------------------------
# This plugin handles XML content in this order:
# 1) Transform the XML content with XSLT
# 2) Replace the value of XPath tags
# 3) Check XML validity against the XSD schema (XSD SOAP and XSD API)
#--------------------------------------------------------------------
class Plugin(object):
    def __init__(self, config):
        self.config = config

    #----------------------------------------------------
    # Executed for every request from a client and 
    # before it is being proxied to the upstream service
    #----------------------------------------------------
    def access(self, kong: kong.kong):
        kong.log.notice("access *** BEGIN ***")
        
        try:
            xmlHReq = XMLHandlingRequest(self.config)
            
            # Transform XML with XSLT Transformation
            xmlHReq.XSLTransform(kong)

            # Replace the value of XPath tags
            xmlHReq.XPathReplace(kong)

            # Validate XML against XSD schema
            xmlHReq.XMLValidate(kong)

        except Exception as ex:
            kong.log.err("XML Handling error, exception= {}".format(ex))
            return

        kong.log.notice("access *** END ***")

# add below section to allow this plugin optionally be running in a dedicated process
if __name__ == "__main__":
    from kong_pdk.cli import start_dedicated_server
    start_dedicated_server("xml-request-handling", Plugin, version, priority, Schema)