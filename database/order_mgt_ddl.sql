-- ========================================
-- SingleStore order_mgt Database DDL
-- Generated on: 2025-09-24
-- Workspace: papalote-ws-2
-- Database: order_mgt
-- ========================================

-- Create database (if needed)
CREATE DATABASE IF NOT EXISTS order_mgt;
USE order_mgt;

-- ========================================
-- Table: contract
-- Purpose: Contract lifecycle management
-- ========================================
CREATE TABLE `contract` (
  `co_contractid` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `co_recordtype` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  `co_contracttype` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  `co_title` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  `co_custkey` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `co_status` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  `co_contractmanager` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `co_amount` decimal(10,0) DEFAULT NULL,
  `co_enddate` datetime DEFAULT NULL,
  `co_datesubmitted` datetime DEFAULT NULL,
  `co_datesent` datetime DEFAULT NULL,
  `co_datesigned` datetime DEFAULT NULL,
  `co_renewaltype` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  `co_slastatus` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  `co_term` int(2) DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FULLTEXT USING VERSION 2 KEY `fts_contract_index` (`co_title`),
  UNIQUE KEY `pk` (`co_contractid`) UNENFORCED RELY,
  SHARD KEY `__SHARDKEY` (`co_contractid`),
  SORT KEY `co_contractid` (`co_contractid`),
  KEY `contract_managers` (`co_contractmanager`) USING HASH,
  KEY `idx_contract_amount_manager` (`co_amount`,`co_contractmanager`) USING HASH,
  KEY `idx_contract_covering_manager_activity` (`co_amount`,`co_contractmanager`,`co_contractid`) USING HASH,
  KEY `idx_contract_status` (`co_status`) USING HASH,
  KEY `idx_contract_summary_covering` (`co_amount`,`co_contractmanager`,`co_status`) USING HASH,
  KEY `idx_contract_custkey` (`co_custkey`) USING HASH
) AUTOSTATS_CARDINALITY_MODE=INCREMENTAL AUTOSTATS_HISTOGRAM_MODE=CREATE AUTOSTATS_SAMPLING=ON SQL_MODE='STRICT_ALL_TABLES,NO_AUTO_CREATE_USER' CHARACTER SET=`utf8mb4` COLLATE=`utf8mb4_general_ci`;

-- ========================================
-- Table: customer
-- Purpose: Customer master data
-- ========================================
CREATE TABLE `customer` (
  `c_custkey` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `c_name` varchar(25) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `c_address` varchar(40) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `c_nationkey` int(11) NOT NULL,
  `c_phone` char(15) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `c_acctbal` decimal(15,2) NOT NULL,
  `c_mktsegment` varchar(20) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `c_comment` varchar(200) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FULLTEXT USING VERSION 2 KEY `fts_customer_index` (`c_name`),
  UNIQUE KEY `pk` (`c_custkey`) UNENFORCED RELY,
  SHARD KEY `__SHARDKEY` (`c_custkey`),
  SORT KEY `c_custkey` (`c_custkey`)
) AUTOSTATS_CARDINALITY_MODE=INCREMENTAL AUTOSTATS_HISTOGRAM_MODE=CREATE AUTOSTATS_SAMPLING=ON SQL_MODE='STRICT_ALL_TABLES,NO_AUTO_CREATE_USER' CHARACTER SET=`utf8mb4` COLLATE=`utf8mb4_general_ci`;

-- ========================================
-- Table: employee
-- Purpose: Employee master data
-- ========================================
CREATE TABLE `employee` (
  `e_empkey` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `e_name` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `e_email` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `e_role` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  UNIQUE KEY `pk` (`e_empkey`) USING HASH,
  SHARD KEY `__SHARDKEY` (`e_empkey`),
  SORT KEY `e_empkey` (`e_empkey`)
) AUTOSTATS_CARDINALITY_MODE=INCREMENTAL AUTOSTATS_HISTOGRAM_MODE=CREATE AUTOSTATS_SAMPLING=ON SQL_MODE='STRICT_ALL_TABLES,NO_AUTO_CREATE_USER' CHARACTER SET=`utf8mb4` COLLATE=`utf8mb4_general_ci`;

-- ========================================
-- Table: lineitem
-- Purpose: Order line items
-- ========================================
CREATE TABLE `lineitem` (
  `l_orderkey` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `l_partkey` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `l_suppkey` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `l_linenumber` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `l_quantity` decimal(15,2) NOT NULL,
  `l_extendedprice` decimal(15,2) NOT NULL,
  `l_discount` decimal(15,2) NOT NULL,
  `l_tax` decimal(15,2) NOT NULL,
  `l_returnflag` char(1) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `l_linestatus` char(1) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `l_shipdate` date NOT NULL,
  `l_commitdate` date NOT NULL,
  `l_receiptdate` date NOT NULL,
  `l_shipinstruct` char(25) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `l_shipmode` char(10) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `l_comment` varchar(44) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `pk` (`l_orderkey`,`l_linenumber`) UNENFORCED RELY,
  SHARD KEY `__SHARDKEY` (`l_orderkey`),
  SORT KEY `l_orderkey` (`l_orderkey`)
) AUTOSTATS_CARDINALITY_MODE=INCREMENTAL AUTOSTATS_HISTOGRAM_MODE=CREATE AUTOSTATS_SAMPLING=ON SQL_MODE='STRICT_ALL_TABLES,NO_AUTO_CREATE_USER' CHARACTER SET=`utf8mb4` COLLATE=`utf8mb4_general_ci`;

-- ========================================
-- Table: nation
-- Purpose: Nation/country reference data
-- ========================================
CREATE TABLE `nation` (
  `n_nationkey` int(11) NOT NULL,
  `n_name` char(25) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `n_regionkey` int(11) NOT NULL,
  `n_comment` varchar(152) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  UNIQUE KEY `pk` (`n_nationkey`) UNENFORCED RELY,
  SHARD KEY `__SHARDKEY` (`n_nationkey`),
  SORT KEY `n_nationkey` (`n_nationkey`)
) AUTOSTATS_CARDINALITY_MODE=INCREMENTAL AUTOSTATS_HISTOGRAM_MODE=CREATE AUTOSTATS_SAMPLING=ON SQL_MODE='STRICT_ALL_TABLES,NO_AUTO_CREATE_USER' CHARACTER SET=`utf8mb4` COLLATE=`utf8mb4_general_ci`;

-- ========================================
-- Table: orders
-- Purpose: Order header information
-- ========================================
CREATE TABLE `orders` (
  `o_orderkey` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `o_custkey` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `o_orderstatus` char(1) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `o_totalprice` decimal(15,2) NOT NULL,
  `o_orderdate` date NOT NULL,
  `o_orderpriority` char(15) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `o_clerk` varchar(36) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `o_shippriority` int(11) NOT NULL,
  `o_comment` varchar(79) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `pk` (`o_orderkey`) UNENFORCED RELY,
  SHARD KEY `__SHARDKEY` (`o_orderkey`),
  SORT KEY `o_orderkey` (`o_orderkey`)
) AUTOSTATS_CARDINALITY_MODE=INCREMENTAL AUTOSTATS_HISTOGRAM_MODE=CREATE AUTOSTATS_SAMPLING=ON SQL_MODE='STRICT_ALL_TABLES,NO_AUTO_CREATE_USER' CHARACTER SET=`utf8mb4` COLLATE=`utf8mb4_general_ci`;

-- ========================================
-- Table: part
-- Purpose: Parts/products catalog
-- ========================================
CREATE TABLE `part` (
  `p_partkey` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `p_name` varchar(55) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `p_mfgr` char(25) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `p_brand` char(10) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `p_type` varchar(25) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `p_size` int(11) NOT NULL,
  `p_container` char(10) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `p_retailprice` decimal(15,2) NOT NULL,
  `p_comment` varchar(23) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `pk` (`p_partkey`) UNENFORCED RELY,
  SHARD KEY `__SHARDKEY` (`p_partkey`),
  SORT KEY `p_partkey` (`p_partkey`),
  FULLTEXT USING VERSION 1 KEY `p_name` (`p_name`,`p_comment`)
) AUTOSTATS_CARDINALITY_MODE=INCREMENTAL AUTOSTATS_HISTOGRAM_MODE=CREATE AUTOSTATS_SAMPLING=ON SQL_MODE='STRICT_ALL_TABLES,NO_AUTO_CREATE_USER' CHARACTER SET=`utf8mb4` COLLATE=`utf8mb4_general_ci`;

-- ========================================
-- Table: partsupp
-- Purpose: Part supplier relationships
-- ========================================
CREATE TABLE `partsupp` (
  `ps_partkey` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `ps_suppkey` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `ps_availqty` int(11) NOT NULL,
  `ps_supplycost` decimal(15,2) NOT NULL,
  `ps_comment` varchar(199) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  UNIQUE KEY `pk` (`ps_partkey`,`ps_suppkey`) UNENFORCED RELY,
  SHARD KEY `__SHARDKEY` (`ps_partkey`),
  SORT KEY `ps_partkey` (`ps_partkey`,`ps_suppkey`)
) AUTOSTATS_CARDINALITY_MODE=INCREMENTAL AUTOSTATS_HISTOGRAM_MODE=CREATE AUTOSTATS_SAMPLING=ON SQL_MODE='STRICT_ALL_TABLES,NO_AUTO_CREATE_USER' CHARACTER SET=`utf8mb4` COLLATE=`utf8mb4_general_ci`;

-- ========================================
-- Table: record_metadata
-- Purpose: Audit trail and metadata tracking
-- ========================================
CREATE TABLE `record_metadata` (
  `record_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `table_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '',
  `created_by` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `updated_by` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `deleted_at` datetime DEFAULT NULL,
  `deleted_by` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `record_owner` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `tenant_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `metadata` JSON COLLATE utf8mb4_bin,
  PRIMARY KEY (`record_id`,`table_name`),
  KEY `idx_deleted_records` (`table_name`,`deleted_at`) USING HASH,
  KEY `idx_owner_records` (`record_owner`,`table_name`) USING HASH,
  KEY `idx_tenant_records` (`tenant_id`,`table_name`) USING HASH,
  SHARD KEY `__SHARDKEY` (`record_id`,`table_name`),
  SORT KEY `__UNORDERED` ()
) AUTOSTATS_CARDINALITY_MODE=INCREMENTAL AUTOSTATS_HISTOGRAM_MODE=CREATE AUTOSTATS_SAMPLING=ON SQL_MODE='STRICT_ALL_TABLES,NO_AUTO_CREATE_USER' CHARACTER SET=`utf8mb4` COLLATE=`utf8mb4_general_ci`;

-- ========================================
-- Table: region
-- Purpose: Regional reference data
-- ========================================
CREATE TABLE `region` (
  `r_regionkey` int(11) NOT NULL,
  `r_name` char(25) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `r_comment` varchar(152) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  UNIQUE KEY `pk` (`r_regionkey`) UNENFORCED RELY,
  SHARD KEY `__SHARDKEY` (`r_regionkey`),
  SORT KEY `r_regionkey` (`r_regionkey`)
) AUTOSTATS_CARDINALITY_MODE=INCREMENTAL AUTOSTATS_HISTOGRAM_MODE=CREATE AUTOSTATS_SAMPLING=ON SQL_MODE='STRICT_ALL_TABLES,NO_AUTO_CREATE_USER' CHARACTER SET=`utf8mb4` COLLATE=`utf8mb4_general_ci`;

-- ========================================
-- Database Summary:
-- Total Tables: 10
-- Main Entities: contracts, customers, employees, orders, parts
-- Reference Data: nations, regions
-- Support Tables: lineitem, partsupp, record_metadata
-- 
-- Key Features:
-- - UUID-based primary keys for most entities
-- - Full-text search indexes on key text fields
-- - Comprehensive audit trail via record_metadata
-- - Sharding and sorting optimized for SingleStore
-- - Created/updated timestamp tracking
-- ========================================