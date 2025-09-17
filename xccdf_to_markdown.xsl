<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xccdf="http://checklists.nist.gov/xccdf/1.2"
    xmlns:xccdf11="http://checklists.nist.gov/xccdf/1.1"
    xmlns:dc="http://purl.org/dc/elements/1.1/">

    <xsl:output method="text" encoding="UTF-8"/>
    <xsl:strip-space elements="*"/>

    <!-- This template matches the root of the document -->
    <xsl:template match="/">
        <xsl:apply-templates select="//xccdf:Benchmark | //xccdf11:Benchmark"/>
    </xsl:template>

    <!-- Template for the main Benchmark element (XCCDF 1.2) -->
    <xsl:template match="xccdf:Benchmark">
        <xsl:text># STIG Benchmark: </xsl:text>
        <xsl:value-of select="xccdf:title"/>
        <xsl:text>&#xa;&#xa;---&#xa;&#xa;</xsl:text>
        
        <xsl:text>**Version:** </xsl:text>
        <xsl:value-of select="xccdf:version"/>
        <xsl:text>&#xa;&#xa;</xsl:text>
        
        <xsl:text>**Description:**&#xa;</xsl:text>
        <xsl:value-of select="normalize-space(xccdf:description)"/>
        <xsl:text>&#xa;&#xa;</xsl:text>

        <!-- Process all groups and rules within the benchmark -->
        <xsl:apply-templates select="xccdf:Group | xccdf:Rule"/>
    </xsl:template>

    <!-- Template for the main Benchmark element (XCCDF 1.1) -->
    <xsl:template match="xccdf11:Benchmark">
        <xsl:text># STIG Benchmark: </xsl:text>
        <xsl:value-of select="xccdf11:title"/>
        <xsl:text>&#xa;&#xa;---&#xa;&#xa;</xsl:text>
        
        <xsl:text>**Version:** </xsl:text>
        <xsl:value-of select="xccdf11:version"/>
        <xsl:text>&#xa;&#xa;</xsl:text>
        
        <xsl:text>**Description:**&#xa;</xsl:text>
        <xsl:value-of select="normalize-space(xccdf11:description)"/>
        <xsl:text>&#xa;&#xa;</xsl:text>

        <!-- Process all groups and rules within the benchmark -->
        <xsl:apply-templates select="xccdf11:Group | xccdf11:Rule"/>
    </xsl:template>

    <!-- Template for Group elements (XCCDF 1.2) -->
    <xsl:template match="xccdf:Group">
        <xsl:text>## Group: </xsl:text>
        <xsl:value-of select="xccdf:title"/>
        <xsl:text>&#xa;&#xa;</xsl:text>
        <xsl:text>**Group ID:** `</xsl:text>
        <xsl:value-of select="@id"/>
        <xsl:text>`&#xa;&#xa;</xsl:text>
        
        <!-- Recursively apply templates to nested groups and rules -->
        <xsl:apply-templates select="xccdf:Group | xccdf:Rule"/>
    </xsl:template>

    <!-- Template for Group elements (XCCDF 1.1) -->
    <xsl:template match="xccdf11:Group">
        <xsl:text>## Group: </xsl:text>
        <xsl:value-of select="xccdf11:title"/>
        <xsl:text>&#xa;&#xa;</xsl:text>
        <xsl:text>**Group ID:** `</xsl:text>
        <xsl:value-of select="@id"/>
        <xsl:text>`&#xa;&#xa;</xsl:text>
        
        <!-- Recursively apply templates to nested groups and rules -->
        <xsl:apply-templates select="xccdf11:Group | xccdf11:Rule"/>
    </xsl:template>

    <!-- Template for Rule elements (XCCDF 1.2) -->
    <xsl:template match="xccdf:Rule">
        <xsl:text>### Rule: </xsl:text>
        <xsl:value-of select="xccdf:title"/>
        <xsl:text>&#xa;&#xa;</xsl:text>
        
        <xsl:text>**Rule ID:** `</xsl:text>
        <xsl:value-of select="@id"/>
        <xsl:text>`&#xa;</xsl:text>
        
        <xsl:text>**Severity:** </xsl:text>
        <xsl:value-of select="@severity"/>
        <xsl:text>&#xa;&#xa;</xsl:text>
        
        <xsl:text>**Description:**&#xa;</xsl:text>
        <xsl:value-of select="normalize-space(xccdf:description)"/>
        <xsl:text>&#xa;&#xa;</xsl:text>

        <xsl:text>**Check Text:**&#xa;</xsl:text>
        <xsl:value-of select="normalize-space(xccdf:check/xccdf:check-content)"/>
        <xsl:text>&#xa;&#xa;</xsl:text>
    </xsl:template>

    <!-- Template for Rule elements (XCCDF 1.1) -->
    <xsl:template match="xccdf11:Rule">
        <xsl:text>### Rule: </xsl:text>
        <xsl:value-of select="xccdf11:title"/>
        <xsl:text>&#xa;&#xa;</xsl:text>
        
        <xsl:text>**Rule ID:** `</xsl:text>
        <xsl:value-of select="@id"/>
        <xsl:text>`&#xa;</xsl:text>
        
        <xsl:text>**Severity:** </xsl:text>
        <xsl:value-of select="@severity"/>
        <xsl:text>&#xa;&#xa;</xsl:text>
        
        <xsl:text>**Description:**&#xa;</xsl:text>
        <xsl:value-of select="normalize-space(xccdf11:description)"/>
        <xsl:text>&#xa;&#xa;</xsl:text>

        <xsl:text>**Check Text:**&#xa;</xsl:text>
        <xsl:value-of select="normalize-space(xccdf11:check/xccdf11:check-content)"/>
        <xsl:text>&#xa;&#xa;</xsl:text>
    </xsl:template>

</xsl:stylesheet>